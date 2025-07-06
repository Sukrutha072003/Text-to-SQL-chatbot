# Text-to-SQL Chatbot (Dockerized)

A natural language interface to SQL databases powered by **Gemini 1.5 Flash**, built using **LangChain**, **FastAPI**, and **Streamlit**. This chatbot enables users to ask questions in plain English and receive the corresponding SQL queries and database results. The entire application is containerized using **Docker** for consistent and portable deployment.

---

## Key Features

- Converts natural language queries into SQL using **Gemini 1.5 Flash**
- Built with **LangChain** and `langchain-google-genai`
- FastAPI-based backend with RESTful API endpoints
- Streamlit frontend for user interaction
- Utilizes the **Chinook sample SQLite database**
- Dockerized application with `docker-compose` support
- Supports `.env` configuration for secure API key management

---

## Technology Stack

| Layer              | Technology                          |
|--------------------|--------------------------------------|
| Large Language Model | Gemini 1.5 Flash (Google Generative AI) |
| NLP Framework      | LangChain + langchain-google-genai  |
| Backend            | FastAPI, Uvicorn, Gunicorn          |
| Frontend           | Streamlit                           |
| Database           | SQLite (Chinook)                    |
| Containerization   | Docker, Docker Compose              |
