#!/usr/bin/env python3
"""Setup the default user for the system."""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, 'local.env'))


def setup_default_user():
    """Setup the default user via API call."""
    print("Setting up default user...")
    
    try:
        # Make API call to setup default user
        response = requests.post("http://localhost:8000/auth/setup-default-user")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Default user setup successful!")
            print(f"User: {result.get('user', {}).get('email', 'Unknown')}")
            print(f"User ID: {result.get('user', {}).get('user_id', 'Unknown')}")
            return True
        else:
            print(f"❌ Setup failed: {response.status_code}")
            try:
                error = response.json()
                print(f"Error: {error.get('detail', 'Unknown error')}")
            except:
                print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the server is running on localhost:8000")
        print("Run: ./run_all_oncloud.sh")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_login():
    """Test login with the default user."""
    print("\nTesting login...")
    
    try:
        login_data = {
            "email": "huynguyenvt1989@gmail.com",
            "password": "Vungtau1989"
        }
        
        response = requests.post("http://localhost:8000/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"Token: {result.get('token', 'No token')[:50]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            try:
                error = response.json()
                print(f"Error: {error.get('detail', 'Unknown error')}")
            except:
                print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main function."""
    print("Default User Setup Script")
    print("=" * 30)
    
    # Setup default user
    setup_success = setup_default_user()
    
    if setup_success:
        # Test login
        login_success = test_login()
        
        if login_success:
            print("\n🎉 Setup and authentication working correctly!")
            print("\nYou can now:")
            print("1. Login with email: huynguyenvt1989@gmail.com")
            print("2. Password: Vungtau1989")
            print("3. Access all your documents and data")
        else:
            print("\n⚠️ Setup succeeded but login test failed")
    else:
        print("\n❌ Setup failed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())