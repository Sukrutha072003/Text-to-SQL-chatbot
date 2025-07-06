from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_community.utilities import SQLDatabase
import os
from typing import Optional

app = FastAPI(title="Text-to-SQL API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    sql_query: Optional[str] = None
    error: Optional[str] = None

# Global variables
llm = None
db = None
sql_chain = None

# Initialize LLM
def init_llm():
    global llm
    if llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
    return llm

# Initialize database
def init_database():
    global db
    if db is None:
        db_path = os.getenv("DATABASE_PATH", "C:/Users/sukru/projects/text-to-sql/data/chinook.db")
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    return db

# Get database schema
def get_table_details():
    return """
Database Schema:
- customers: CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId
- invoices: InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total
- invoice_items: InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity
- tracks: TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice
- albums: AlbumId, Title, ArtistId
- artists: ArtistId, Name
- genres: GenreId, Name
- media_types: MediaTypeId, Name
- playlists: PlaylistId, Name
- playlist_track: PlaylistId, TrackId
- employees: EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email
"""

# Few-shot examples
examples = [
    {
        "input": "Which customers are from Brazil?",
        "query": "SELECT FirstName, LastName, Country FROM customers WHERE Country = 'Brazil';"
    },
    {
        "input": "What are the names of all tracks in the 'Rock' genre?",
        "query": """SELECT t.Name FROM tracks t
JOIN genres g ON t.GenreId = g.GenreId
WHERE g.Name = 'Rock'
LIMIT 10;"""
    },
    {
        "input": "What are the top 5 most expensive tracks?",
        "query": "SELECT Name, UnitPrice FROM tracks ORDER BY UnitPrice DESC LIMIT 5;"
    },
    {
        "input": "How many customers are there in total?",
        "query": "SELECT COUNT(*) as total_customers FROM customers;"
    },
    {
        "input": "What are the names of all albums by the artist 'AC/DC'?",
        "query": """SELECT al.Title FROM albums al
JOIN artists ar ON al.ArtistId = ar.ArtistId
WHERE ar.Name = 'AC/DC';"""
    }
]

def create_sql_chain():
    global sql_chain
    if sql_chain is None:
        llm = init_llm()
        
        # Create few-shot prompt template
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{query}")
        ])
        
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples,
            input_variables=["input"],
        )
        
        # Main system prompt
        system_message = f"""You are a SQLite expert. Your task is to convert natural language questions into syntactically correct SQLite queries.

{get_table_details()}

IMPORTANT RULES:
1. Return ONLY the SQL query, nothing else
2. Do not include any explanations, comments, or markdown formatting
3. Use proper SQLite syntax
4. Always use proper JOINs when connecting tables
5. Limit results to reasonable numbers (use LIMIT when appropriate)
6. Use proper column names as specified in the schema
7. For text comparisons, use single quotes
8. End queries with semicolon

Here are some examples of good queries:"""
        
        # Create the final prompt
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            few_shot_prompt,
            ("human", "{input}")
        ])
        
        sql_chain = final_prompt | llm | StrOutputParser()
    
    return sql_chain

def clean_sql_query(sql_response):
    """Clean the SQL response to extract just the query"""
    # Remove common prefixes and suffixes
    sql = sql_response.strip()
    
    # Remove markdown code blocks
    sql = re.sub(r'```sql\n?', '', sql)
    sql = re.sub(r'```\n?', '', sql)
    
    # Remove common prefixes
    sql = re.sub(r'^(SQL Query:|Query:|SQL:)\s*', '', sql, flags=re.IGNORECASE)
    
    # Remove any trailing explanations (text after the semicolon)
    if ';' in sql:
        sql = sql.split(';')[0] + ';'
    
    return sql.strip()

def execute_sql_safely(db, query):
    """Execute SQL query with proper error handling"""
    try:
        result = db.run(query)
        return result, None
    except Exception as e:
        return None, str(e)

def format_sql_result(result, question, query):
    """Format the SQL result into a natural language response"""
    if not result or result.strip() == "":
        return "No results found for your query."
    
    # For simple counting queries
    if "COUNT" in query.upper():
        return f"The result is: {result}"
    
    # For other queries, provide a more natural response
    return f"Here are the results:\n\n{result}"

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        init_llm()
        init_database()
        create_sql_chain()
        print("✅ Application initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize application: {str(e)}")
        raise

@app.get("/")
async def root():
    return {"message": "Text-to-SQL API is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "text-to-sql-api"}

@app.get("/schema")
async def get_schema():
    """Get the database schema"""
    return {"schema": get_table_details()}

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process natural language query and return SQL result"""
    try:
        # Get initialized components
        db = init_database()
        chain = create_sql_chain()
        
        # Generate SQL query
        raw_sql = chain.invoke({"input": request.question})
        cleaned_sql = clean_sql_query(raw_sql)
        
        # Execute SQL
        result, error = execute_sql_safely(db, cleaned_sql)
        
        if error:
            return QueryResponse(
                success=False,
                sql_query=cleaned_sql,
                error=f"SQL execution error: {error}"
            )
        
        # Format result
        formatted_result = format_sql_result(result, request.question, cleaned_sql)
        
        return QueryResponse(
            success=True,
            result=formatted_result,
            sql_query=cleaned_sql
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)