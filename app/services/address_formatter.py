from typing import Optional, List, Dict


class AddressFormatter:
    """
    Dynamically formats address fields into clean human-readable strings
    without awkward empty commas or gaps.
    """

    @staticmethod
    def _clean_join(parts: List[Optional[str]], separator: str = ", ") -> str:
        """Filter out None, empty strings, and whitespace, then join with separator."""
        cleaned = [p.strip() for p in parts if p and p.strip()]
        return separator.join(cleaned)

    @classmethod
    def format_full(cls, address) -> str:
        """
        FULL address format:
        Combines business name, house, street/road, building/floor, town/area, landmark,
        tehsil, city, district, province/state, postal code, and country.
        """
        biz_part = address.business_name if getattr(address, "business_name", None) else None
        # Primary building/street component
        house_part = f"House {address.house_number}" if address.house_number else None
        floor_part = f"Floor {address.floor}" if address.floor else None
        flat_part = f"Flat {address.flat}" if address.flat else None
        bldg_part = address.building

        building_info = cls._clean_join([biz_part, house_part, flat_part, floor_part, bldg_part], " ")

        street_part = address.street
        road_part = address.road
        street_info = cls._clean_join([street_part, road_part], " / ")

        area_info = cls._clean_join([address.area, address.locality, address.town])
        landmark_info = f"Near {address.landmark}" if address.landmark and not address.landmark.lower().startswith("near ") else address.landmark

        city_part = address.city
        tehsil_part = address.tehsil if address.tehsil and address.tehsil != address.city else None
        district_part = address.district if address.district and address.district != address.city else None
        province_part = address.province_state
        postal_part = address.postal_code
        country_part = address.country

        parts = [
            building_info,
            street_info,
            area_info,
            landmark_info,
            tehsil_part,
            city_part,
            district_part,
            province_part,
            postal_part,
            country_part
        ]
        return cls._clean_join(parts, ", ")

    @classmethod
    def format_local(cls, address) -> str:
        """LOCAL format: Business, House, Street, Area/Town, City."""
        biz_part = address.business_name if getattr(address, "business_name", None) else None
        house_part = f"House {address.house_number}" if address.house_number else None
        building_info = cls._clean_join([biz_part, house_part, address.building], " ")
        street_info = cls._clean_join([address.street, address.road], " / ")
        area_info = cls._clean_join([address.area, address.town])
        
        parts = [building_info, street_info, area_info, address.city]
        return cls._clean_join(parts, ", ")

    @classmethod
    def format_delivery(cls, address) -> str:
        """DELIVERY format: Business, House, Street, Landmark, City."""
        biz_part = address.business_name if getattr(address, "business_name", None) else None
        house_part = f"House {address.house_number}" if address.house_number else None
        building_info = cls._clean_join([biz_part, house_part, address.building], " ")
        street_info = cls._clean_join([address.street, address.road], " / ")
        landmark_info = f"Near {address.landmark}" if address.landmark and not address.landmark.lower().startswith("near ") else address.landmark

        parts = [building_info, street_info, landmark_info, address.city]
        return cls._clean_join(parts, ", ")

    @classmethod
    def format_landmark(cls, address) -> str:
        """LANDMARK format: Landmark and City."""
        landmark_info = f"Near {address.landmark}" if address.landmark and not address.landmark.lower().startswith("near ") else address.landmark
        parts = [landmark_info, address.city, address.country]
        return cls._clean_join(parts, ", ")

    @classmethod
    def format_gps(cls, address) -> Optional[str]:
        """GPS format: latitude, longitude."""
        if address.latitude is not None and address.longitude is not None:
            return f"{address.latitude:.5f}, {address.longitude:.5f}"
        return None

    @classmethod
    def format_all_views(cls, address) -> Dict[str, str]:
        """Return dict of all available formats."""
        res = {
            "FULL": cls.format_full(address),
            "LOCAL": cls.format_local(address),
            "DELIVERY": cls.format_delivery(address),
            "LANDMARK": cls.format_landmark(address) if address.landmark else cls.format_local(address),
        }
        gps = cls.format_gps(address)
        if gps:
            res["GPS"] = gps
        return res
