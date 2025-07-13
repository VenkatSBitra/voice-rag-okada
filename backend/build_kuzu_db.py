import kuzu
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()
client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"

def clean_and_convert_to_numeric(series: pd.Series) -> pd.Series:
    """Helper function to clean currency/string data into a numeric format."""
    # Coerce errors will turn any values that can't be converted into NaN (Not a Number)
    return pd.to_numeric(series.astype(str).str.replace('[$,]', '', regex=True), errors='coerce')

def process_csv_to_kuzu_db(csv_path: str, db_path: str):
    """
    Reads a CSV, cleans specified columns into numeric types while retaining the
    original text, and loads the data into a Kuzu graph.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at '{csv_path}'")
        return

    print(f"Reading data from '{csv_path}'...")
    df = pd.read_csv(csv_path)

    # --- 1. Sanitize Column Names ---
    df.columns = df.columns.str.replace(' ', '_').str.replace(r'[\(\)/]', '_', regex=True).str.replace(r'__', '_', regex=True)

    # --- 2. Clean Data & Create Numeric Columns ---
    print("Cleaning data and creating numeric columns...")
    # For Listings
    df['rent_sf_year_numeric'] = clean_and_convert_to_numeric(df['Rent_SF_Year'])
    df['annual_rent_numeric'] = clean_and_convert_to_numeric(df['Annual_Rent'])
    df['monthly_rent_numeric'] = clean_and_convert_to_numeric(df['Monthly_Rent'])
    # For Brokers
    df['gci_3_years_numeric'] = clean_and_convert_to_numeric(df['GCI_On_3_Years'])

    print(f"Generating vector embeddings with OpenAI ('{EMBEDDING_MODEL}')...")
    try:
        # Get embeddings for the 'Property_Address' column
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=df['Property_Address'].tolist()
        )
        # Extract the embedding vectors from the response
        address_embeddings = [item.embedding for item in response.data]
        df['address_embedding'] = [json.dumps(e) for e in address_embeddings]

    except Exception as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return

    # --- 3. Initialize Kuzu Database ---
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # --- 4. Define the Updated Graph Schema ---
    print("Defining updated graph schema in Kuzu...")
    # Node tables with both text and numeric columns
    conn.execute("""
        CREATE NODE TABLE Broker(
            email STRING,
            gci_3_years_text STRING,
            gci_3_years_numeric DOUBLE,
            PRIMARY KEY (email)
        )
    """)
    conn.execute("CREATE NODE TABLE Associate(name STRING, PRIMARY KEY (name))")
    conn.execute("""
        CREATE NODE TABLE Listing(
            unique_id STRING,
            address STRING,
            floor STRING,
            suite STRING,
            size_sf DOUBLE,
            rent_sf_year_text STRING,
            annual_rent_text STRING,
            monthly_rent_text STRING,
            rent_sf_year_numeric DOUBLE,
            annual_rent_numeric DOUBLE,
            monthly_rent_numeric DOUBLE,

            address_embedding STRING,

            PRIMARY KEY (unique_id)
        )
    """)

    # Relationship tables (no changes here)
    conn.execute("CREATE REL TABLE WorksWith(FROM Broker TO Associate)")
    conn.execute("CREATE REL TABLE Manages(FROM Broker TO Listing)")


    # --- 5. Prepare DataFrames for Loading ---
    print("Preparing DataFrames for loading...")
    # Broker DataFrame
    brokers_df = df[['BROKER_Email_ID', 'GCI_On_3_Years', 'gci_3_years_numeric']].drop_duplicates(subset='BROKER_Email_ID').dropna(subset=['BROKER_Email_ID'])
    brokers_df = brokers_df.rename(columns={'BROKER_Email_ID': 'email', 'GCI_On_3_Years': 'gci_3_years_text'})
    
    # Listing DataFrame
    listings_df = df[[
        'unique_id', 'Property_Address', 'Floor', 'Suite', 'Size_SF_',
        'Rent_SF_Year', 'Annual_Rent', 'Monthly_Rent',
        'rent_sf_year_numeric', 'annual_rent_numeric', 'monthly_rent_numeric', 'address_embedding'
    ]].copy()
    listings_df = listings_df.rename(columns={
        'Property_Address': 'address', 'Size_SF_': 'size_sf',
        'Rent_SF_Year': 'rent_sf_year_text', 'Annual_Rent': 'annual_rent_text', 'Monthly_Rent': 'monthly_rent_text'
    })

    # Associate DataFrame
    all_associates = pd.concat([df['Associate_1'], df['Associate_2'], df['Associate_3'], df['Associate_4']]).dropna().unique()
    associates_df = pd.DataFrame(all_associates, columns=['name'])
    
    # Relationship DataFrames
    works_with_dfs = []
    for col in ['Associate_1', 'Associate_2', 'Associate_3', 'Associate_4']:
        works_with_df = df[['BROKER_Email_ID', col]].dropna().rename(columns={'BROKER_Email_ID': 'FROM', col: 'TO'})
        works_with_dfs.append(works_with_df)
    all_works_with_df = pd.concat(works_with_dfs)

    manages_df = df[['BROKER_Email_ID', 'unique_id']].rename(columns={'BROKER_Email_ID': 'FROM', 'unique_id': 'TO'})

    # --- 6. Load Data into Kuzu ---
    print("Loading data into Kuzu...")
    conn.execute("COPY Broker FROM brokers_df")
    conn.execute("COPY Listing FROM listings_df")
    conn.execute("COPY Associate FROM associates_df")
    conn.execute("COPY WorksWith FROM all_works_with_df")
    conn.execute("COPY Manages FROM manages_df")

    print("\nKuzu database created successfully with text and numeric columns!")

if __name__ == '__main__':
    csv_file_path = './data/HackathonInternalKnowledgeBase.csv'
    db_file_path = 'kuzu_real_estate_db'
    
    if not os.path.exists(db_file_path):
        os.makedirs(db_file_path)
    
    process_csv_to_kuzu_db(csv_file_path, db_file_path)
