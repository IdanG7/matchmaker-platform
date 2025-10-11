# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

As this project is in active development (pre-1.0), we recommend always using the latest release.

## Reporting a Vulnerability

We take the security of the Matchmaker Platform seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do Not Disclose Publicly

Please do not open a public GitHub issue for security vulnerabilities. Public disclosure before a fix is available puts all users at risk.

### 2. Report via GitHub Security Advisories

Report security vulnerabilities through [GitHub Security Advisories](https://github.com/IdanG7/matchmaker-platform/security/advisories/new).

Alternatively, you can email security reports to: [your-email@example.com]

### 3. Include Detailed Information

Help us understand and reproduce the issue by including:

- **Type of vulnerability** (e.g., authentication bypass, SQL injection, XSS)
- **Affected component** (API, SDK, specific service)
- **Version affected** (commit SHA or release version)
- **Steps to reproduce** the vulnerability
- **Proof of concept** (if possible)
- **Potential impact** of the vulnerability
- **Suggested fix** (if you have one)

### 4. Response Timeline

- **Initial Response**: Within 48 hours
- **Severity Assessment**: Within 5 business days
- **Patch Development**: Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days)
- **Public Disclosure**: After patch is released or 90 days, whichever comes first

### 5. Security Advisory Process

Once we receive your report:

1. We will acknowledge receipt within 48 hours
2. We will assess the severity using CVSS 3.1
3. We will develop a fix in a private security branch
4. We will release a security patch
5. We will publish a security advisory crediting you (unless you prefer anonymity)
6. We will notify users to update via GitHub releases and advisories

## Vulnerability Severity Guidelines

We use the [CVSS 3.1](https://www.first.org/cvss/calculator/3.1) scoring system:

- **Critical (9.0-10.0)**: Remote code execution, authentication bypass
- **High (7.0-8.9)**: Privilege escalation, sensitive data exposure
- **Medium (4.0-6.9)**: DoS attacks, information disclosure
- **Low (0.1-3.9)**: Minor issues with limited impact

## Security Best Practices for Users

### For Developers Integrating the SDK

1. **Keep Dependencies Updated**: Regularly update the SDK and game client
2. **Secure Token Storage**: Never commit JWT tokens or API keys to version control
3. **Validate Server Messages**: Don't trust data from WebSocket without validation
4. **Use HTTPS**: Always connect to the API over HTTPS in production
5. **Rate Limiting**: Implement client-side rate limiting to avoid hitting API limits

### For Platform Operators

1. **Environment Variables**: Use environment variables for secrets, never hardcode
2. **Database Security**:
   - Use strong passwords for PostgreSQL
   - Enable SSL/TLS for database connections
   - Restrict database access to service IPs only
3. **Network Security**:
   - Use firewall rules to restrict access
   - Only expose Gateway API to the internet
   - Use VPC/private networks for service-to-service communication
4. **Token Security**:
   - Use strong JWT secret keys (at least 32 characters)
   - Rotate JWT secrets periodically
   - Set appropriate token expiration times
5. **Monitoring**:
   - Enable audit logging
   - Monitor for suspicious activity (failed login attempts, etc.)
   - Set up alerts for security events

## Known Security Considerations

### Current Implementation

- **JWT Secret Key**: Must be configured via environment variable. Default keys in `.env.example` are for development only.
- **Password Hashing**: Uses Bcrypt with salt. Minimum password length: 8 characters.
- **Rate Limiting**: Implemented via Redis. Can be bypassed with IP rotation (future: use user-based limits).
- **WebSocket Authentication**: Tokens passed as query params (visible in logs). Future: upgrade to header-based auth.

### Planned Security Improvements

- [ ] Add role-based access control (RBAC)
- [ ] Implement 2FA for user accounts
- [ ] Add API key rotation for game servers
- [ ] Implement request signing for server-to-server communication
- [ ] Add audit logging for sensitive operations
- [ ] Implement CAPTCHA for registration/login
- [ ] Add IP-based rate limiting in addition to user-based
- [ ] WebSocket authentication via secure headers

## Security Testing

### Automated Security Scanning

Our CI/CD pipeline includes:

- **Bandit**: Static analysis for Python code
- **Trivy**: Vulnerability scanning for dependencies and Docker images
- **Dependency Updates**: Automated via Dependabot

### Manual Security Testing

We encourage security researchers to test the platform responsibly:

- **In Scope**:
  - Authentication and authorization bypass
  - SQL injection, NoSQL injection
  - XSS, CSRF, SSRF
  - Remote code execution
  - Privilege escalation
  - Sensitive data exposure
  - Denial of service (excluding resource exhaustion)

- **Out of Scope**:
  - Social engineering attacks
  - Physical attacks
  - DDoS attacks
  - Issues in third-party dependencies (report to upstream)
  - Issues requiring compromised client or server credentials

### Responsible Disclosure

- Do not access or modify data that does not belong to you
- Do not perform destructive testing (data deletion, DoS)
- Do not pivot to other users' accounts or data
- Limit impact to the minimum necessary to demonstrate vulnerability
- Test against your own deployed instance when possible

## Security Hall of Fame

We recognize security researchers who help improve our security:

| Researcher | Vulnerability | Date | Severity |
|------------|---------------|------|----------|
| _None yet_ | _None yet_    | _N/A_ | _N/A_   |

## Contact

For security concerns: [your-email@example.com]

For general questions: [GitHub Issues](https://github.com/IdanG7/matchmaker-platform/issues)

---

**Last Updated**: October 2025
