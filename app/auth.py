import streamlit as st
from configurations import USERNAME, PASSWORD

def create_login_page():
    """Creates a beautifully designed login page"""
    
    # Center the login form on the page
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <style>
        .login-container {
            background-color: #f8f9fa;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-top: 2rem;
        }
        .title-container {
            text-align: center;
            margin-bottom: 2rem;
        }
        .stButton > button {
            width: 100%;
            margin-top: 1rem;
            background-color: #0d6efd;
            color: white;
        }
        .error-msg {
            text-align: center;
            color: #dc3545;
            padding: 0.5rem;
            margin-top: 1rem;
            border-radius: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # Logo and Title
            st.markdown("""
            <div class="title-container">
                <h1>🚚 CTS Shipping</h1>
                <p>Please log in to access the calculator</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Login Form
            username = st.text_input("Username", key="username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="password", placeholder="Enter your password")
            
            if "login_attempts" not in st.session_state:
                st.session_state.login_attempts = 0
            
            def check_credentials():
                """Validates the user credentials"""
                if username.lower() == USERNAME.lower() and password == PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.login_attempts = 0
                else:
                    st.session_state.authenticated = False
                    st.session_state.login_attempts += 1
            
            st.button("Login", on_click=check_credentials, type="primary")
            
            # Show error message if login fails
            if "authenticated" in st.session_state and not st.session_state.authenticated:
                st.markdown(
                    f'<div class="error-msg">Invalid credentials. Attempts: {st.session_state.login_attempts}</div>',
                    unsafe_allow_html=True
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Footer
            st.markdown("""
            <div style='text-align: center; margin-top: 2rem; color: #6c757d;'>
                <p>© 2025 CTS Shipping Calculator. All rights reserved.</p>
            </div>
            """, unsafe_allow_html=True)

def is_authenticated():
    """Checks if the user is authenticated"""
    return st.session_state.get('authenticated', False)
