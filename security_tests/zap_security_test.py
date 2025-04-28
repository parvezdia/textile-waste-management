#!/usr/bin/env python3
"""
Automated security testing script using OWASP ZAP for the Textile Fabric Waste Management System.
This script performs:
1. Authentication testing
2. Access control testing
3. CSRF protection testing
4. SQL injection testing
5. XSS vulnerability testing
"""

import time
import sys
import os
import logging
from zapv2 import ZAPv2
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_tests/zap_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('zap-security-tests')

# ZAP Configuration
ZAP_API_KEY = 'thub4q6u474ofl0ravrdv1vk87'  # Change this to a secure API key
ZAP_PORT = 8090
ZAP_PROXY = {'http': f'http://localhost:{ZAP_PORT}', 'https': f'http://localhost:{ZAP_PORT}'}
TARGET_URL = 'http://127.0.0.1:8000'  # Django development server URL

# Test user credentials
ADMIN_USER = {'username': 'admin@example.com', 'password': '123'}
NON_ADMIN_USER = {'username': 'buyer1@example.com', 'password': 'password123'}

class ZAPSecurityTester:
    def __init__(self):
        """Initialize the ZAP API client and configure settings."""
        self.zap = None
        self.authenticated = False
        self.session_token = None
        self.target_url = TARGET_URL
        
    def start_zap(self):
        """Connect to ZAP daemon (assuming it's already running)."""
        try:
            self.zap = ZAPv2(apikey=ZAP_API_KEY, proxies=ZAP_PROXY)
            version = self.zap.core.version
            logger.info(f"Connected to ZAP {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ZAP: {e}")
            return False
    
    def authenticate_user(self, username, password):
        """Authenticate to the application and capture session cookies."""
        logger.info(f"Attempting to authenticate as {username}")
        
        # Get CSRF token from login page
        session = requests.Session()
        session.proxies = ZAP_PROXY
        
        login_url = f"{self.target_url}/accounts/login/"
        login_response = session.get(login_url)
        
        # Extract CSRF token (Django uses csrfmiddlewaretoken in forms)
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        
        if not csrf_token:
            logger.error("Failed to obtain CSRF token")
            return False
            
        # Perform login
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Referer': login_url
        }
        
        # Attempt login
        response = session.post(login_url, data=login_data, headers=headers)
        
        # Check if login was successful
        if response.url != login_url:  # If redirected away from login page
            logger.info(f"Authentication successful as {username}")
            
            # Get the session ID and CSRF token for ZAP to use
            cookies = session.cookies.get_dict()
            self.session_token = cookies.get('sessionid', None)
            self.csrf_token = cookies.get('csrftoken', None)
            
            # Set ZAP context authentication details
            self.authenticated = True
            return True
        else:
            logger.error(f"Authentication failed for {username}")
            return False
    
    def setup_context(self, context_name, user_type):
        """Setup a ZAP context with the authenticated user."""
        # Create new context
        context_id = self.zap.context.new_context(context_name)
        logger.info(f"Created context {context_name} with ID {context_id}")
        
        # Add target to context
        self.zap.context.include_in_context(context_name, f"^{self.target_url}.*$")
        
        # Set up session management
        self.zap.sessionManagement.set_session_management_method(
            context_id, 
            'cookieBasedSessionManagement', 
            None
        )
        
        # Setup authentication method
        form_based_config = (
            'loginUrl=' + TARGET_URL + '/accounts/login/&' +
            'loginRequestData=username={%username%}&password={%password%}&csrfmiddlewaretoken={%csrf%}'
        )
        self.zap.authentication.set_authentication_method(
            context_id,
            'formBasedAuthentication',
            form_based_config
        )
        
        # Add logged-in indicator
        self.zap.authentication.set_logged_in_indicator(context_id, "\\QSign Out\\E")
        
        # Add credentials
        if user_type == 'admin':
            user = ADMIN_USER
        else:
            user = NON_ADMIN_USER
            
        user_id = self.zap.users.new_user(context_id, user_type)
        user_auth_config = (
            'username=' + user['username'] + '&' +
            'password=' + user['password']
        )
        self.zap.users.set_authentication_credentials(context_id, user_id, user_auth_config)
        self.zap.users.set_user_enabled(context_id, user_id, True)
        
        logger.info(f"Created {user_type} user in context {context_name}")
        
        return context_id, user_id
    
    def run_spider(self, context_id=None, user_id=None):
        """Run the ZAP spider to discover site content."""
        logger.info("Starting spider scan...")
        
        if context_id and user_id:
            logger.info(f"Running spider as authenticated user in context {context_id}")
            scan_id = self.zap.spider.scan_as_user(context_id, user_id, self.target_url)
        else:
            logger.info("Running spider anonymously")
            scan_id = self.zap.spider.scan(self.target_url)
            
        # Wait for Spider to complete
        time.sleep(2)
        while int(self.zap.spider.status(scan_id)) < 100:
            logger.info(f"Spider progress: {self.zap.spider.status(scan_id)}%")
            time.sleep(2)
            
        logger.info("Spider scan completed")
        
    def run_active_scan(self, context_id=None, user_id=None):
        """Run the ZAP active scanner to find vulnerabilities."""
        logger.info("Starting active scan...")
        
        if context_id and user_id:
            logger.info(f"Running active scan as authenticated user in context {context_id}")
            scan_id = self.zap.ascan.scan_as_user(self.target_url, 0, context_id, user_id)
        else:
            logger.info("Running active scan anonymously")
            scan_id = self.zap.ascan.scan(self.target_url)
            
        # Wait for Active Scanner to complete
        time.sleep(5)
        while int(self.zap.ascan.status(scan_id)) < 100:
            logger.info(f"Active scan progress: {self.zap.ascan.status(scan_id)}%")
            time.sleep(5)
            
        logger.info("Active scan completed")
    
    def test_access_control(self):
        """Test access to restricted endpoints by non-admin user using requests through ZAP proxy."""
        logger.info("Testing access control - non-admin accessing admin endpoints")
        
        # Setup non-admin context (for ZAP scanning, but requests will be used for direct access test)
        context_id, user_id = self.setup_context('non-admin-context', 'non-admin')
        
        # URLs that should be restricted
        admin_urls = [
            '/transactions/create/',
            '/transactions/report/',
            '/admin/',
            '/inventory/manage/',
        ]
        
        # Authenticate as non-admin user using requests
        session = requests.Session()
        session.proxies = ZAP_PROXY
        login_url = f"{self.target_url}/accounts/login/"
        login_page = session.get(login_url)
        # Parse CSRF token from login form
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        if not csrf_token and 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        if not csrf_token:
            logger.error("Failed to obtain CSRF token for non-admin user")
            logger.error(f"Login page HTML: {login_page.text[:500]}")
            return
        login_data = {
            'username': NON_ADMIN_USER['username'],
            'password': NON_ADMIN_USER['password'],
            'csrfmiddlewaretoken': csrf_token
        }
        headers = {'Referer': login_url}
        logger.info(f"Attempting non-admin login with data: {login_data}")
        login_response = session.post(login_url, data=login_data, headers=headers)
        if login_response.url == login_url:
            logger.error("Non-admin login failed; cannot test access control.")
            logger.error(f"Login response HTML: {login_response.text[:500]}" )
            return
        
        for url in admin_urls:
            full_url = f"{self.target_url}{url}"
            logger.info(f"Testing restricted access to: {full_url}")
            response = session.get(full_url, allow_redirects=False)
            status_code = response.status_code
            if status_code in [302, 303, 307, 403]:
                logger.info(f"✓ Access correctly denied to {url} (Status: {status_code})")
            else:
                logger.warning(f"✗ Potential access control issue: {url} returned {status_code}")
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        logger.info("Testing CSRF protection")
        
        # Enable CSRF scanner
        # self.zap.pscan.enable_scanner(10202)  # CSRF Scanner ID
        
        # Setup admin context for testing forms that require authentication
        context_id, user_id = self.setup_context('csrf-test-context', 'admin')
        
        self.zap.forcedUser.set_forced_user_mode_enabled(True)
        self.zap.forcedUser.set_forced_user(context_id, user_id)
        
        # First spider the site as an admin to discover all forms
        self.run_spider(context_id, user_id)
        
        # Then check for CSRF issues in passive scan results
        time.sleep(10)  # Wait for passive scan to finish
        csrf_alerts = self.zap.alert.alerts(baseurl=self.target_url, riskid="Medium")
        # Handle ZAP alert structure
        alert_list = csrf_alerts
        if isinstance(csrf_alerts, dict) and 'alerts' in csrf_alerts:
            alert_list = csrf_alerts['alerts']
        if len(alert_list) > 0:
            logger.warning(f"Found {len(alert_list)} potential CSRF vulnerabilities")
            for alert in alert_list:
                if isinstance(alert, dict) and 'url' in alert:
                    logger.warning(f"CSRF issue found at: {alert['url']}")
                else:
                    logger.warning(f"CSRF issue: {alert}")
        else:
            logger.info("No CSRF vulnerabilities detected - protection working correctly")
    
    def generate_report(self, report_file="security_tests/security_report.html"):
        """Generate a security report with the findings."""
        logger.info("Generating security report...")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        # Generate HTML report
        report = self.zap.core.htmlreport()
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Also get alerts summary
        alerts = self.zap.alert.alerts()
        alerts_by_risk = {}
        
        for alert in alerts:
            risk = alert['risk']
            if risk not in alerts_by_risk:
                alerts_by_risk[risk] = []
            alerts_by_risk[risk].append({
                'name': alert['name'],
                'url': alert['url'],
                'param': alert['param'],
                'confidence': alert['confidence']
            })
        
        # Output summary to log
        logger.info("--- Security Test Summary ---")
        for risk, items in alerts_by_risk.items():
            logger.info(f"{risk} risk issues: {len(items)}")
        logger.info(f"Full report saved to {report_file}")
        
        return report_file
        
    def run_full_security_test(self):
        """Run the complete security testing process."""
        try:
            # Initialize connection to ZAP
            if not self.start_zap():
                logger.error("Failed to connect to ZAP. Is it running?")
                sys.exit(1)
                
            # Spider the site anonymously first
            self.run_spider()
            
            # Run tests as authenticated users
            admin_context, admin_user = self.setup_context('admin-context', 'admin')
            self.run_spider(admin_context, admin_user)
            
            # Test access control
            self.test_access_control()
            
            # Test CSRF protection
            self.test_csrf_protection()
            
            # Run active scan (this will find most security issues)
            self.run_active_scan()
            
            # Generate comprehensive security report
            report_path = self.generate_report()
            
            logger.info(f"Security testing completed. Report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Security test error: {e}")
            sys.exit(1)

def main():
    """Main function to run the security tests."""
    # Create directory for security tests if it doesn't exist
    os.makedirs('security_tests', exist_ok=True)
    
    logger.info("Starting automated security testing with OWASP ZAP")
    
    print("""
    #########################################################
    #     TEXTILE FABRIC WASTE MANAGEMENT SYSTEM            #
    #     Automated Security Testing with OWASP ZAP         #
    #########################################################
    
    Make sure:
    1. Your Django application is running at http://127.0.0.1:8000
    2. OWASP ZAP is running with API enabled on port 8090
    3. You've updated the test credentials in this script
    
    Press Ctrl+C to abort the test at any time.
    """)
    
    # Prompt to confirm testing
    try:
        input("Press Enter to start security testing (or Ctrl+C to abort)...")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    
    tester = ZAPSecurityTester()
    tester.run_full_security_test()

if __name__ == "__main__":
    main()