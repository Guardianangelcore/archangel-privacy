# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please **do not** open a public GitHub issue. Instead:

1. **Email us** with details at security@guardianangel.dev
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce (if applicable)
   - Affected versions/components
   - Potential impact
   - Any suggested fixes

3. **Timeline:**
   - We aim to acknowledge reports within 48 hours
   - We'll provide regular updates on our progress
   - We'll work with you on timeline and disclosure

## Security Best Practices

### Data Protection
- ✅ Review privacy policy regularly
- ✅ Keep security measures updated
- ✅ Report security concerns
- ✅ Follow data protection standards

### Secrets & Credentials
- ❌ Never commit API keys, tokens, or credentials
- ✅ Use GitHub Secrets for CI/CD pipelines
- ✅ Rotate credentials if accidentally exposed

### Code Security
- ✅ Validate all user inputs
- ✅ Use HTTPS for all external communications
- ✅ Keep sensitive logs out of version control
- ✅ Review security warnings in CI/CD

### Dependencies
- ✅ Keep dependencies up to date
- ✅ Monitor security advisories
- ✅ Pin versions to avoid unexpected breaking changes

## Security Scanning

This repository has automated security scanning enabled:

- **Secret Scanning**: Prevents accidental credential commits
- **SAST (Static Analysis)**: Scans for common security issues
- **Code Review**: All PRs require review before merge

## Compliance

- GDPR compliance
- Privacy-first approach
- Transparent data handling
- Regular security assessments

## Additional Resources

- [OWASP Security Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [GDPR Compliance](https://gdpr-info.eu/)
- [Privacy Best Practices](https://www.eff.org/)

---

Last Updated: 2026-10-03