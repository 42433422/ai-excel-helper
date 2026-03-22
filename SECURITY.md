# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| 2.0.x   | :x:                |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

We take the security of XCAGI seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email at [security@example.com](mailto:security@example.com) or create a draft security advisory on GitHub.

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### Information to Include

Please include the following information in your report:

- A description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Any potential impact
- Suggested fixes (if any)

### Process

1. **Initial Response**: Within 48 hours, we will acknowledge your report
2. **Investigation**: We will investigate the issue within 5 business days
3. **Fix Development**: We will work on a fix and test it thoroughly
4. **Release**: We will release a patched version and credit you (if desired)
5. **Disclosure**: After 30 days, we may disclose the issue publicly

## Security Best Practices

### For Users

1. **Environment Variables**: Never commit sensitive information like API keys or passwords
2. **Database Security**: Use strong passwords for database access
3. **HTTPS**: Always use HTTPS in production environments
4. **Regular Updates**: Keep your dependencies up to date
5. **Access Control**: Implement proper authentication and authorization

### For Contributors

1. **Code Review**: All code changes must be reviewed
2. **Testing**: Security-sensitive code must have tests
3. **Documentation**: Document security implications
4. **Input Validation**: Always validate and sanitize user input
5. **Error Handling**: Never expose sensitive information in error messages

## Security Features

XCAGI includes several security features:

- **Password Hashing**: Passwords are hashed using bcrypt
- **Session Management**: Secure session handling with expiration
- **CORS Protection**: Configurable CORS policies
- **Rate Limiting**: Protection against brute-force attacks
- **Input Sanitization**: Protection against SQL injection and XSS
- **Database Isolation**: Separate database files for different data types

## Known Limitations

- SQLite database files should be properly backed up and protected
- Local deployment requires proper system security
- API keys must be managed securely by the user

## Contact

For security-related questions, please contact:
- Email: [security@example.com](mailto:security@example.com)
- GitHub Security Advisories: https://github.com/42433422/xcagi/security/advisories

---

**Last Updated**: 2026-03-23
