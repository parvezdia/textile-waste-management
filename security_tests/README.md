# Security Testing with OWASP ZAP

This directory contains scripts for automated security testing of the Textile Fabric Waste Management System using OWASP ZAP.

## Prerequisites

1. **Install OWASP ZAP**: Download and install from [OWASP ZAP website](https://www.zaproxy.org/download/)
2. **Python Dependencies**: Make sure you have installed the required Python packages:
   ```
   pip install python-owasp-zap-v2.4 requests
   ```

## Setting Up OWASP ZAP

1. **Launch OWASP ZAP**:
   - Start ZAP application from your start menu or applications folder
   - When prompted, select "No, I do not want to persist the session at this moment"

2. **Configure API Settings**:
   - Go to Tools -> Options -> API
   - Make sure "Enabled" is checked
   - Generate a new API Key or set it to match the one in the script (ZAP_API_KEY)
   - Set the Address to listen on as "localhost" and Port to "8090"

3. **Update Script Settings**:
   - Open `zap_security_test.py` and update these values:
     - `ZAP_API_KEY`: Your ZAP API key from the previous step
     - `TARGET_URL`: Your Django application URL (default: http://127.0.0.1:8000)
     - `ADMIN_USER` and `NON_ADMIN_USER`: Valid credentials for your system

## Running the Security Tests

1. **Start your Django application**:
   ```
   python manage.py runserver
   ```

2. **Run the security test script**:
   ```
   python security_tests/zap_security_test.py
   ```

3. **Monitor the output**:
   - The script will create logs in the `security_tests` directory
   - Progress will be shown in the console
   - A final HTML report will be generated at `security_tests/security_report.html`

## Security Tests Performed

The script automatically performs the following security tests:

1. **Authentication Testing**: Verifies the login functionality works properly
2. **Access Control Testing**: Ensures non-admin users can't access admin-only pages
3. **CSRF Protection Testing**: Checks that forms are protected against CSRF attacks
4. **Active Scanning**: Runs ZAP's active scanner to find common vulnerabilities:
   - SQL Injection
   - Cross-Site Scripting (XSS)
   - Path Traversal
   - Information Disclosure
   - And many other OWASP Top 10 vulnerabilities

## Interpreting Results

The security scan produces two main outputs:

1. **Console/Log Output**: Shows progress and high-level findings
2. **HTML Report**: Detailed report with all findings, including:
   - Risk level (High, Medium, Low, Informational)
   - Description of each vulnerability
   - Evidence found
   - Suggested solutions

Focus on addressing High and Medium risk issues first. For each finding:
1. Confirm it's a genuine issue (some may be false positives)
2. Understand the vulnerability and its impact
3. Apply the recommended fix
4. Re-run the test to verify the fix worked

## Manual Testing Follow-up

After automated testing, consider these manual security checks:

1. **Additional CSRF Tests**: Try removing CSRF tokens from forms manually
2. **Session Management**: Test session timeouts and concurrent session handling
3. **Password Policy**: Verify password requirements are enforced
4. **File Upload**: Test uploading potentially malicious files

## Security Recommendations

Based on initial code review, consider implementing these security improvements:

1. Move `SECRET_KEY` to environment variables
2. Set `DEBUG = False` in production
3. Enable secure cookies in production:
   ```python
   CSRF_COOKIE_SECURE = True
   SESSION_COOKIE_SECURE = True
   ```
4. Add HTTP security headers:
   ```python
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   ```