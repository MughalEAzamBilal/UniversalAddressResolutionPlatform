from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.advertisement import Advertisement, AdPlacement, AdType


class AdService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_ads(self, placement: Optional[str] = None) -> List[Advertisement]:
        """Fetch active ads, optionally filtered by placement, ordered by display order."""
        query = self.db.query(Advertisement).filter(Advertisement.is_active == True)
        if placement:
            query = query.filter(Advertisement.placement == placement)
        return query.order_by(Advertisement.display_order.asc(), Advertisement.created_at.desc()).all()

    def get_all_ads(self) -> List[Advertisement]:
        """List all ads for administrator view."""
        return self.db.query(Advertisement).order_by(Advertisement.display_order.asc(), Advertisement.created_at.desc()).all()

    def get_ad_by_id(self, ad_id: int) -> Optional[Advertisement]:
        return self.db.query(Advertisement).filter(Advertisement.id == ad_id).first()

    def create_ad(
        self,
        title: str,
        placement: str,
        ad_type: str = AdType.GOOGLE_ADSENSE,
        code_snippet: Optional[str] = None,
        image_url: Optional[str] = None,
        target_url: Optional[str] = None,
        is_active: bool = True,
        display_order: int = 0
    ) -> Advertisement:
        ad = Advertisement(
            title=title.strip(),
            placement=placement.strip(),
            ad_type=ad_type.strip(),
            code_snippet=code_snippet.strip() if code_snippet else None,
            image_url=image_url.strip() if image_url else None,
            target_url=target_url.strip() if target_url else None,
            is_active=is_active,
            display_order=display_order
        )
        self.db.add(ad)
        self.db.commit()
        self.db.refresh(ad)
        return ad

    def update_ad(
        self,
        ad_id: int,
        title: Optional[str] = None,
        placement: Optional[str] = None,
        ad_type: Optional[str] = None,
        code_snippet: Optional[str] = None,
        image_url: Optional[str] = None,
        target_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        display_order: Optional[int] = None
    ) -> Optional[Advertisement]:
        ad = self.get_ad_by_id(ad_id)
        if not ad:
            return None
        if title is not None:
            ad.title = title.strip()
        if placement is not None:
            ad.placement = placement.strip()
        if ad_type is not None:
            ad.ad_type = ad_type.strip()
        if code_snippet is not None:
            ad.code_snippet = code_snippet.strip() if code_snippet else None
        if image_url is not None:
            ad.image_url = image_url.strip() if image_url else None
        if target_url is not None:
            ad.target_url = target_url.strip() if target_url else None
        if is_active is not None:
            ad.is_active = is_active
        if display_order is not None:
            ad.display_order = display_order
        self.db.commit()
        self.db.refresh(ad)
        return ad

    def toggle_active(self, ad_id: int) -> Optional[Advertisement]:
        ad = self.get_ad_by_id(ad_id)
        if not ad:
            return None
        ad.is_active = not ad.is_active
        self.db.commit()
        self.db.refresh(ad)
        return ad

    def delete_ad(self, ad_id: int) -> bool:
        ad = self.get_ad_by_id(ad_id)
        if not ad:
            return False
        self.db.delete(ad)
        self.db.commit()
        return True

    def record_impression(self, ad_id: int):
        ad = self.get_ad_by_id(ad_id)
        if ad:
            ad.impressions += 1
            self.db.commit()

    def record_click(self, ad_id: int):
        ad = self.get_ad_by_id(ad_id)
        if ad:
            ad.clicks += 1
            self.db.commit()

    def get_stats(self) -> Dict[str, int]:
        total_ads = self.db.query(Advertisement).count()
        active_ads = self.db.query(Advertisement).filter(Advertisement.is_active == True).count()
        total_impressions = self.db.query(func.sum(Advertisement.impressions)).scalar() or 0
        total_clicks = self.db.query(func.sum(Advertisement.clicks)).scalar() or 0
        
        # Placements count
        placements_count = {}
        for p in AdPlacement.ALL:
            placements_count[p] = self.db.query(Advertisement).filter(Advertisement.placement == p).count()

        return {
            "total_ads": total_ads,
            "active_ads": active_ads,
            "inactive_ads": total_ads - active_ads,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "placements": placements_count
        }
