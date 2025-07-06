import streamlit as st
import requests
import json
import os

# Set up the page
st.set_page_config(page_title="Text-to-SQL Chatbot", page_icon="💬")
st.title("🧠 Text-to-SQL Chatbot with Gemini")
st.caption("Ask your question in natural language, and get a SQL result from the Chinook database.")

# Backend API URL
API_URL = os.getenv("API_URL", "http://backend:8000")

def get_database_schema():
    """Get database schema from backend"""
    try:
        response = requests.get(f"{API_URL}/schema", timeout=10)
        if response.status_code == 200:
            return response.json()["schema"]
        else:
            return "Unable to fetch database schema"
    except Exception as e:
        return f"Error fetching schema: {str(e)}"

def query_backend(question):
    """Send question to backend and get response"""
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Backend error: {response.status_code} - {response.text}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

def check_backend_health():
    """Check if backend is healthy"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    # Check backend health
    if not check_backend_health():
        st.error("🔴 Backend service is not available. Please check your backend connection.")
        st.info(f"Trying to connect to: {API_URL}")
        return
    
    # Show database schema in sidebar
    with st.sidebar:
        st.header("📊 Database Schema")
        schema = get_database_schema()
        st.text(schema)
        
        # Add some example questions
        st.header("💡 Example Questions")
        example_questions = [
            "How many customers are from each country?",
            "What are the top 10 best-selling tracks?",
            "Which artist has the most albums?",
            "What is the total revenue by year?",
            "Show me all customers from Canada",
            "Which customers are from Brazil?",
            "What are the names of all tracks in the 'Rock' genre?",
            "What are the top 5 most expensive tracks?"
        ]
        
        for eq in example_questions:
            if st.button(eq, key=f"example_{eq[:20]}", use_container_width=True):
                st.session_state.example_question = eq
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "sql" in message and message["sql"]:
                with st.expander("🔍 Generated SQL"):
                    st.code(message["sql"], language="sql")
    
    # Handle example question selection
    if hasattr(st.session_state, 'example_question'):
        user_input = st.session_state.example_question
        del st.session_state.example_question
    else:
        user_input = st.chat_input("Type your question here...")
    
    # Process user input
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Query backend and display response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = query_backend(user_input)
                
                if response["success"]:
                    # Display result
                    st.write(response["result"])
                    
                    # Show the generated SQL
                    if response.get("sql_query"):
                        with st.expander("🔍 Generated SQL Query"):
                            st.code(response["sql_query"], language="sql")
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["result"],
                        "sql": response.get("sql_query", "")
                    })
                else:
                    # Display error
                    error_msg = f"❌ {response['error']}"
                    st.error(error_msg)
                    
                    # Add error message to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "sql": response.get("sql_query", "")
                    })
    
    # Add a clear chat button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh Connection", use_container_width=True):
            st.rerun()
    
    # Display connection status
    st.sidebar.markdown("---")
    if check_backend_health():
        st.sidebar.success("🟢 Backend Connected")
    else:
        st.sidebar.error("🔴 Backend Disconnected")
    
    st.sidebar.text(f"API URL: {API_URL}")

if __name__ == "__main__":
    main()