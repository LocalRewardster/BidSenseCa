from datetime import datetime, timedelta, timezone
import uuid
from typing import List, Dict, Any

from app.services.database import db_service


class SampleDataService:
    """Service for adding sample data to the database."""
    
    @staticmethod
    def get_sample_tenders() -> List[Dict[str, Any]]:
        """Get sample tender data."""
        now = datetime.now(timezone.utc)
        
        return [
            {
                "id": str(uuid.uuid4()),
                "title": "Highway Maintenance Services - Ontario",
                "organization": "Ministry of Transportation Ontario",
                "description": "Comprehensive highway maintenance services including snow removal, road repairs, and infrastructure maintenance across Ontario highways.",
                "contract_value": "$2.5M",
                "source_name": "Ontario Portal",
                "location": "Ontario",
                "url": "https://example.com/tender1",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "IT System Modernization Project",
                "organization": "Department of Technology and Innovation",
                "description": "Modernization of legacy IT systems including database upgrades, cloud migration, and security enhancements.",
                "contract_value": "$1.8M",
                "source_name": "CanadaBuys",
                "location": "Quebec",
                "url": "https://example.com/tender2",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Healthcare Equipment Supply and Maintenance",
                "organization": "Health Canada",
                "description": "Supply and maintenance of medical equipment for federal healthcare facilities including diagnostic machines and patient monitoring systems.",
                "contract_value": "$3.2M",
                "source_name": "Alberta Purchasing",
                "location": "Alberta",
                "url": "https://example.com/tender3",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Environmental Assessment Services",
                "organization": "Environment and Climate Change Canada",
                "description": "Environmental impact assessments for infrastructure projects including wildlife studies, air quality monitoring, and sustainability reporting.",
                "contract_value": "$950K",
                "source_name": "BC Bid",
                "location": "British Columbia",
                "url": "https://example.com/tender4",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Educational Technology Platform Development",
                "organization": "Department of Education",
                "description": "Development of a comprehensive online learning platform for federal educational programs including course management and student tracking systems.",
                "contract_value": "$4.1M",
                "source_name": "Manitoba",
                "location": "Manitoba",
                "url": "https://example.com/tender5",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Public Safety Communication Systems",
                "organization": "Public Safety Canada",
                "description": "Upgrade and maintenance of emergency communication systems for law enforcement and emergency response agencies.",
                "contract_value": "$2.8M",
                "source_name": "Saskatchewan",
                "location": "Saskatchewan",
                "url": "https://example.com/tender6",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Cultural Heritage Preservation Project",
                "organization": "Canadian Heritage",
                "description": "Preservation and digitization of historical documents and artifacts including archival storage systems and public access platforms.",
                "contract_value": "$1.5M",
                "source_name": "Quebec",
                "location": "Quebec",
                "url": "https://example.com/tender7",
                "scraped_at": now.isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Transportation Infrastructure Planning",
                "organization": "Transport Canada",
                "description": "Comprehensive planning services for national transportation infrastructure including feasibility studies and environmental assessments.",
                "contract_value": "$3.7M",
                "source_name": "Ontario Portal",
                "location": "Ontario",
                "url": "https://example.com/tender8",
                "scraped_at": now.isoformat(),
            },
        ]
    
    @staticmethod
    async def add_sample_data() -> int:
        """Add sample data to the database."""
        try:
            sample_tenders = SampleDataService.get_sample_tenders()
            count = 0
            
            for tender_data in sample_tenders:
                result = await db_service.create_tender(tender_data)
                if result:
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error adding sample data: {e}")
            return 0


# Function to easily add sample data
async def add_sample_tenders():
    """Add sample tenders to the database."""
    count = await SampleDataService.add_sample_data()
    print(f"Added {count} sample tenders to the database")
    return count 