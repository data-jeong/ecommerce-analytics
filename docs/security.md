# Security Documentation

## Authentication & Authorization

### JWT Authentication

1. **Token Generation**:

```python
def generate_jwt_token(user_id: int, expiry_minutes: int = 60) -> str:
    payload = {
        'sub': str(user_id),
        'exp': datetime.utcnow() + timedelta(minutes=expiry_minutes),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')
```

2. **Token Validation**:

```python
def validate_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token has expired')
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')
```

### API Key Authentication

1. **API Key Generation**:

```python
def generate_api_key(user_id: int) -> str:
    key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(
        f"{key}{API_KEY_SALT}".encode()
    ).hexdigest()
    store_api_key(user_id, hashed_key)
    return key
```

2. **API Key Validation**:

```python
def validate_api_key(api_key: str) -> bool:
    hashed_key = hashlib.sha256(
        f"{api_key}{API_KEY_SALT}".encode()
    ).hexdigest()
    return verify_stored_api_key(hashed_key)
```

## Authorization

### Role-Based Access Control (RBAC)

1. **Role Definitions**:

```python
ROLES = {
    'admin': {
        'permissions': ['read', 'write', 'delete', 'manage_users'],
        'scope': 'global'
    },
    'analyst': {
        'permissions': ['read', 'write'],
        'scope': 'analytics'
    },
    'viewer': {
        'permissions': ['read'],
        'scope': 'analytics'
    }
}
```

2. **Permission Check**:

```python
def check_permission(user_role: str, required_permission: str) -> bool:
    if user_role not in ROLES:
        return False
    return required_permission in ROLES[user_role]['permissions']
```

## Data Protection

### Encryption at Rest

1. **Database Encryption**:

```sql
-- Enable encryption for RDS instance
aws rds modify-db-instance \
    --db-instance-identifier ecommerce-analytics \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:region:account:key/key-id
```

2. **Sensitive Data Handling**:

```python
def mask_sensitive_data(data: dict) -> dict:
    sensitive_fields = ['email', 'phone', 'address']
    for field in sensitive_fields:
        if field in data:
            data[field] = f"{data[field][:3]}***{data[field][-2:]}"
    return data
```

### Encryption in Transit

1. **SSL/TLS Configuration**:

```python
ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.load_verify_locations(cafile="/path/to/ca.pem")
```

2. **HTTPS Enforcement**:

```python
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if request.url.scheme != "https":
        url = request.url.replace(scheme="https")
        return RedirectResponse(url, status_code=301)
    return await call_next(request)
```

## Input Validation & Sanitization

### Request Validation

1. **Input Sanitization**:

```python
def sanitize_input(value: str) -> str:
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>\'";]', '', value)
    # Escape HTML entities
    return html.escape(sanitized)
```

2. **Schema Validation**:

```python
class AnalyticsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    metrics: List[str]
    dimensions: Optional[List[str]]
    filters: Optional[Dict[str, Any]]

    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
```

## Rate Limiting

### Implementation

1. **Rate Limit Configuration**:

```python
RATE_LIMITS = {
    'default': {
        'requests': 1000,
        'period': 3600  # 1 hour
    },
    'analytics': {
        'requests': 100,
        'period': 3600
    }
}
```

2. **Rate Limit Middleware**:

```python
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    endpoint = request.url.path

    # Get rate limit for endpoint
    limit = RATE_LIMITS.get(endpoint, RATE_LIMITS['default'])

    # Check rate limit
    if await is_rate_limited(client_ip, endpoint, limit):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )

    return await call_next(request)
```

## Security Headers

### Implementation

1. **Security Headers Middleware**:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response
```

## Audit Logging

### Implementation

1. **Audit Log Schema**:

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    resource = Column(String)
    details = Column(JSON)
```

2. **Audit Logging Function**:

```python
async def log_audit_event(
    user_id: int,
    action: str,
    resource: str,
    details: dict
) -> None:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details
    )
    db.add(audit_log)
    await db.commit()
```

## Security Monitoring

### Implementation

1. **Failed Login Monitoring**:

```python
async def monitor_failed_logins(user_id: int, ip_address: str) -> None:
    key = f"failed_login:{user_id}:{ip_address}"
    count = await redis.incr(key)
    await redis.expire(key, 3600)  # 1 hour

    if count >= 5:
        await block_ip_address(ip_address)
        await notify_security_team(
            f"Multiple failed login attempts for user {user_id} from {ip_address}"
        )
```

2. **Suspicious Activity Detection**:

```python
async def detect_suspicious_activity(request: Request) -> bool:
    indicators = [
        check_request_rate(request),
        check_unusual_patterns(request),
        check_known_bad_actors(request)
    ]

    if any(indicators):
        await log_security_event(request)
        return True
    return False
```

## Incident Response

### Procedures

1. **Security Incident Response**:

```python
async def handle_security_incident(incident: dict) -> None:
    # 1. Log incident
    await log_security_event(incident)

    # 2. Block suspicious activity
    if incident.get('ip_address'):
        await block_ip_address(incident['ip_address'])

    # 3. Notify security team
    await notify_security_team(incident)

    # 4. Take remediation actions
    await execute_remediation_plan(incident)
```

2. **Automated Response**:

```python
async def execute_remediation_plan(incident: dict) -> None:
    actions = {
        'brute_force': revoke_user_sessions,
        'data_leak': rotate_api_keys,
        'unauthorized_access': lock_user_account
    }

    if incident['type'] in actions:
        await actions[incident['type']](incident)
```

## Regular Security Reviews

### Checklist

1. **Weekly Security Review**:

- Review audit logs for suspicious patterns
- Check failed login attempts
- Monitor API usage patterns
- Review access control changes
- Check for outdated dependencies

2. **Monthly Security Tasks**:

- Rotate access credentials
- Review security policies
- Update security documentation
- Conduct vulnerability scans
- Review incident response procedures
