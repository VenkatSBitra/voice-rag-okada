import pandas as pd
import sqlite3
import os

def process_csv_to_normalized_db(csv_path: str, db_path: str):
    """
    Reads a real estate CSV, normalizes the data into three tables 
    (listings, brokers, associates), and saves it to a SQLite database.

    Args:
        csv_path (str): The path to the source CSV file.
        db_path (str): The path to save the output SQLite database file.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at '{csv_path}'")
        return

    print(f"Reading data from '{csv_path}'...")
    df = pd.read_csv(csv_path)

    # --- 1. Sanitize Column Names for SQL ---
    # Replaces spaces and special characters to make names SQL-friendly
    original_cols = df.columns
    df.columns = df.columns.str.replace(' ', '_').str.replace(r'[\(\)/]', '_', regex=True).str.replace(r'__', '_', regex=True)

    # Store the mapping for clarity if needed later
    column_mapping = dict(zip(original_cols, df.columns))
    print("\nSanitized column names for SQL compatibility.")
    
    # --- 2. Create the 'brokers' DataFrame ---
    # This table holds unique information about each broker.
    print("Creating 'brokers' table data...")
    brokers_df = df[['BROKER_Email_ID', 'GCI_On_3_Years']].copy()
    brokers_df = brokers_df.drop_duplicates(subset='BROKER_Email_ID').dropna(subset=['BROKER_Email_ID'])
    brokers_df = brokers_df.rename(columns={'BROKER_Email_ID': 'broker_email'})
    
    # --- 3. Create the 'associates' DataFrame ---
    # This unpivots the multiple associate columns into a clean, long format.
    print("Creating 'associates' table data...")
    associate_cols = ['Associate_1', 'Associate_2', 'Associate_3', 'Associate_4']
    associates_df = pd.melt(
        df,
        id_vars=['BROKER_Email_ID'],
        value_vars=associate_cols,
        var_name='associate_level', # e.g., 'Associate_1'
        value_name='associate_name'
    )
    # Clean up and remove entries where there was no associate
    associates_df = associates_df.dropna(subset=['associate_name'])
    associates_df = associates_df.rename(columns={'BROKER_Email_ID': 'broker_email'})
    associates_df = associates_df[['broker_email', 'associate_name']] # We don't need the 'associate_level' column

    # --- 4. Create the 'listings' DataFrame ---
    # This is the main table with listing-specific info and a foreign key.
    print("Creating 'listings' table data...")
    listing_cols = [
        'unique_id', 'Property_Address', 'Floor', 'Suite', 'Size_SF_', 
        'Rent_SF_Year', 'Annual_Rent', 'Monthly_Rent', 'BROKER_Email_ID'
    ]
    listings_df = df[listing_cols].copy()
    listings_df = listings_df.rename(columns={'BROKER_Email_ID': 'broker_email', 'SIZE_SF_': 'size_sf', 'RENT_SF_YEAR': 'rent_sf_year'})

    # --- 5. Write DataFrames to SQLite Database ---
    print(f"\nWriting to database '{db_path}'...")
    try:
        conn = sqlite3.connect(db_path)
        
        # Use to_sql to create and populate the tables
        brokers_df.to_sql('brokers', conn, if_exists='replace', index=False)
        associates_df.to_sql('associates', conn, if_exists='replace', index=False)
        listings_df.to_sql('listings', conn, if_exists='replace', index=False)

        # It's good practice to add indexes on foreign keys for faster joins
        cursor = conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_broker_email ON listings(broker_email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_associates_broker_email ON associates(broker_email);")
        conn.commit()
        
        print("\nDatabase created successfully with 3 normalized tables:")
        print(f" - brokers: {len(brokers_df)} rows")
        print(f" - associates: {len(associates_df)} rows")
        print(f" - listings: {len(listings_df)} rows")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# --- HOW TO RUN ---
if __name__ == '__main__':
    csv_file_path = '/Users/venkatsbitra/Documents/Hackathons/Okada/experiements/data/HackathonInternalKnowledgeBase.csv'
    
    # Define file paths
    db_file_path = 'normalized_real_estate.db'
    
    # Run the processing function
    process_csv_to_normalized_db(csv_file_path, db_file_path)