#!/usr/bin/env python3
"""
Quick Security Test Script for Textile Fabric Waste Management System.
This script focuses specifically on:
1. Access Control Testing (Test 1): Try accessing transactions as a non-admin
2. CSRF Protection Testing (Test 2): Validate CSRF protection on forms
"""

import requests
import sys
import time
from bs4 import BeautifulSoup
import logging
import os

# Ensure the log directory exists before setting up logging
os.makedirs('security_tests', exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_tests/quick_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('quick-security-tests')

# Configuration
ZAP_API_KEY = 'thub4q6u474ofl0ravrdv1vk87'
ZAP_PORT = 8090
ZAP_PROXY = {'http': f'http://localhost:{ZAP_PORT}', 'https': f'http://localhost:{ZAP_PORT}'}
TARGET_URL = 'http://127.0.0.1:8000'  # Django development server URL
ADMIN_USER = {'email': 'admin@example.com', 'password': '123'}
NON_ADMIN_USER = {'email': 'buyer1@example.com', 'password': 'password123'}

class QuickSecurityTester:
    def __init__(self):
        """Initialize the security tester with sessions for different users."""
        self.admin_session = requests.Session()
        self.non_admin_session = requests.Session()
        self.target_url = TARGET_URL
        
    def login(self, session, email, password):
        """Log in to the application with the given credentials."""
        logger.info(f"Attempting to authenticate as {email}")
        
        # Get login page to retrieve CSRF token
        login_url = f"{self.target_url}/accounts/login/"
        response = session.get(login_url)
        
        # Parse CSRF token from the page
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        # If no CSRF token in form, try from cookie
        if not csrf_token and 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
            
        if not csrf_token:
            logger.error(f"Failed to obtain CSRF token for {email}")
            return False
            
        # Perform login
        login_data = {
            'email': email,
            'password': password,
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Referer': login_url
        }
        
        # Submit login form
        response = session.post(login_url, data=login_data, headers=headers)
        
        # Check if login was successful by checking for redirection
        if response.url != login_url:  # If redirected away from login page
            logger.info(f"PASS: Authentication successful as {email}")
            return True
        else:
            logger.error(f"FAIL: Authentication failed for {email}")
            return False
            
    def test_access_control(self):
        """Test 1: Try accessing transactions as a non-admin; ensure access is denied."""
        logger.info("\n=== TEST 1: ACCESS CONTROL TESTING ===")
        logger.info("Testing if non-admin users are correctly restricted from admin areas")
        
        # First, login as non-admin user
        if not self.login(self.non_admin_session, NON_ADMIN_USER['email'], NON_ADMIN_USER['password']):
            logger.error("Cannot proceed with access control test - login failed")
            return False
            
        # List of admin-only URLs to test
        admin_urls = [
            '/transactions/report/',
            '/accounts/admin/dashboard/',
            '/accounts/admin/orders/',
            '/accounts/admin/analytics/',
            '/accounts/admin/sustainability/',
            '/accounts/admin/designers/'
        ]
        
        results = []
        
        # Test each admin URL with non-admin user
        for url in admin_urls:
            full_url = f"{self.target_url}{url}"
            logger.info(f"Testing access to restricted URL: {full_url}")
            
            response = self.non_admin_session.get(full_url, allow_redirects=False)
            
            # Check if access was denied - should get 302 redirect or 403 forbidden
            if response.status_code in [302, 303, 307, 403]:
                logger.info(f"PASS: Access correctly denied to {url} (Status: {response.status_code})")
                results.append({
                    'url': url,
                    'status': 'PASS',
                    'code': response.status_code,
                    'details': 'Access correctly denied'
                })
            else:
                logger.warning(f"FAIL: Access control failure on {url} (Status: {response.status_code})")
                results.append({
                    'url': url,
                    'status': 'FAIL',
                    'code': response.status_code,
                    'details': 'Access control bypass possible'
                })
                
        # Count and report results
        passed = len([r for r in results if r['status'] == 'PASS'])
        failed = len([r for r in results if r['status'] == 'FAIL'])
        
        logger.info(f"\nACCESS CONTROL TEST SUMMARY: {passed}/{len(results)} tests passed")
        if failed > 0:
            logger.warning(f"WARNING: Found {failed} access control vulnerabilities")
        else:
            logger.info("PASS: All access control tests passed successfully")
            
        return results
        
    def test_csrf_protection(self):
        """Test 2: Attempt CSRF attack on a form; verify CSRF protection is active."""
        logger.info("\n=== TEST 2: CSRF PROTECTION TESTING ===")
        logger.info("Testing if forms are protected against CSRF attacks")
        
        # First, login as admin user who can access forms
        if not self.login(self.admin_session, ADMIN_USER['email'], ADMIN_USER['password']):
            logger.error("Cannot proceed with CSRF test - admin login failed")
            return False
            
        # List of forms to test CSRF protection
        forms_to_test = [
            {
                'url': '/inventory/waste/upload/',
                'post_data': {'name': 'CSRF Test Waste', 'quantity': '10'}
            },
            {
                'url': '/accounts/profile/',
                'post_data': {'first_name': 'CSRF', 'last_name': 'Test'}
            },
            {
                'url': '/accounts/register/',
                'post_data': {'email': 'csrf-test@example.com', 'password1': 'testpass123', 'password2': 'testpass123', 'user_type': 'DESIGNER'}
            }
        ]
        
        results = []
        
        # Test each form by attempting to submit without CSRF token
        for form in forms_to_test:
            url = form['url']
            post_data = form['post_data']
            full_url = f"{self.target_url}{url}"
            
            logger.info(f"Testing CSRF protection on form: {full_url}")
            
            # Create a new session without CSRF token to simulate attack
            csrf_test_session = requests.Session()
            
            # Try to submit the form without a CSRF token
            response = csrf_test_session.post(full_url, data=post_data)
            
            # Check response - should be 403 Forbidden if CSRF protection works
            if response.status_code == 403:
                logger.info(f"PASS: CSRF protection working correctly on {url}")
                results.append({
                    'url': url,
                    'status': 'PASS',
                    'code': response.status_code,
                    'details': 'CSRF protection active'
                })
            else:
                logger.warning(f"FAIL: CSRF protection may be missing on {url} (Status: {response.status_code})")
                results.append({
                    'url': url,
                    'status': 'FAIL',
                    'code': response.status_code,
                    'details': 'Form submission without CSRF token succeeded'
                })
                
        # Now test with a valid session but manipulated token
        logger.info("Testing with an invalid CSRF token")
        
        # Get a form page first to see how it normally works
        form_url = f"{self.target_url}/transactions/create/"
        response = self.admin_session.get(form_url)
        
        if response.status_code == 200:
            # Parse the page to find the CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            
            if csrf_input:
                # Found a token, now try to submit with a manipulated one
                post_data = {'amount': '100', 'description': 'CSRF Test', 'csrfmiddlewaretoken': 'invalid_token'}
                
                response = self.admin_session.post(form_url, data=post_data)
                
                # Check if the invalid token was rejected
                if response.status_code == 403:
                    logger.info("PASS: Invalid CSRF token correctly rejected")
                    results.append({
                        'url': form_url,
                        'status': 'PASS',
                        'code': response.status_code,
                        'details': 'Invalid CSRF token rejected'
                    })
                else:
                    logger.warning(f"FAIL: Form accepted invalid CSRF token (Status: {response.status_code})")
                    results.append({
                        'url': form_url, 
                        'status': 'FAIL',
                        'code': response.status_code,
                        'details': 'Invalid CSRF token accepted'
                    })
        
        # Count and report results
        passed = len([r for r in results if r['status'] == 'PASS'])
        failed = len([r for r in results if r['status'] == 'FAIL'])
        
        logger.info(f"\nCSRF PROTECTION TEST SUMMARY: {passed}/{len(results)} tests passed")
        if failed > 0:
            logger.warning(f"WARNING: Found {failed} CSRF vulnerabilities")
        else:
            logger.info("PASS: All CSRF protection tests passed successfully")
            
        return results
        
    def run_tests(self):
        """Run all security tests and compile results."""
        logger.info("\n===============================================")
        logger.info("TEXTILE FABRIC WASTE MANAGEMENT SYSTEM")
        logger.info("QUICK SECURITY TEST - FOCUSED ON ACCESS CONTROL & CSRF")
        logger.info("===============================================\n")
        
        # Run access control test
        access_results = self.test_access_control()
        
        # Run CSRF protection test
        csrf_results = self.test_csrf_protection()
        
        # Compile overall results
        logger.info("\n===============================================")
        logger.info("SECURITY TEST SUMMARY")
        logger.info("===============================================")
        
        if isinstance(access_results, list):
            access_passed = len([r for r in access_results if r['status'] == 'PASS'])
            access_failed = len([r for r in access_results if r['status'] == 'FAIL'])
            logger.info(f"Access Control Tests: {access_passed} passed, {access_failed} failed")
            
        if isinstance(csrf_results, list):
            csrf_passed = len([r for r in csrf_results if r['status'] == 'PASS'])
            csrf_failed = len([r for r in csrf_results if r['status'] == 'FAIL'])
            logger.info(f"CSRF Protection Tests: {csrf_passed} passed, {csrf_failed} failed")
            
        if (isinstance(access_results, list) and access_failed > 0) or (isinstance(csrf_results, list) and csrf_failed > 0):
            logger.warning("\nWARNING: Security vulnerabilities detected! Review the log for details.")
        else:
            logger.info("\nPASS: All security tests passed successfully!")
            
        logger.info("\nDetailed results are available in security_tests/quick_test_results.log")
        
def main():
    """Main function to run the quick security tests."""
    print("""
    #########################################################
    #     TEXTILE FABRIC WASTE MANAGEMENT SYSTEM            #
    #     Quick Security Test - Access Control & CSRF       #
    #########################################################
    
    Make sure:
    1. Your Django application is running at http://127.0.0.1:8000
    2. You've updated the test credentials in this script
    3. You have Beautiful Soup installed (pip install beautifulsoup4)
    
    Press Ctrl+C to abort the test at any time.
    """)
    
    # Prompt to confirm testing
    try:
        input("Press Enter to start security testing (or Ctrl+C to abort)...")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    
    # Check if Beautiful Soup is installed
    try:
        import bs4
    except ImportError:
        print("Error: Beautiful Soup not installed. Run 'pip install beautifulsoup4' and try again.")
        sys.exit(1)
    
    tester = QuickSecurityTester()
    tester.run_tests()

if __name__ == "__main__":
    main()