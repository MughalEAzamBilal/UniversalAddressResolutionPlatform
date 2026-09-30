from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.resolver import ResolutionResponse, ResolutionRequest
from app.services.resolver_service import ResolverService
from app.api.deps import get_client_ip
from app.core.security import rate_limiter
from app.core.exceptions import AppError

router = APIRouter(prefix="/resolve", tags=["Public Resolver"])


@router.get("/{public_id}", response_model=ResolutionResponse)
def resolve_address_get(
    public_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public Address Resolution Endpoint.
    Resolves a 6-character Public Address ID into a clean formatted physical address.
    Logs access attempt and enforces rate limiting.
    Does NOT expose personal or internal database information.
    """
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(f"resolve_{ip}", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many resolution requests.")

    service = ResolverService(db)
    try:
        user_agent = request.headers.get("user-agent")
        referrer = request.headers.get("referer")
        return service.resolve(
            public_id=public_id,
            ip_address=ip,
            user_agent=user_agent,
            referrer=referrer
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("", response_model=ResolutionResponse)
def resolve_address_post(
    req: ResolutionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """POST variant for programmatic API resolution (e.g. keyboard extensions, mobile apps)."""
    return resolve_address_get(req.public_id, request, db)
