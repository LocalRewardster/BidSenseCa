-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create users table for authentication and preferences
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    preferences JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true
);

-- Create tenders table
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL, -- 'merx', 'bcbid', 'buyandsell', 'sasktenders'
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    buyer TEXT,
    province TEXT,
    naics TEXT,
    deadline DATE,
    summary_ai TEXT,
    tags_ai TEXT[],
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for tenders table
CREATE UNIQUE INDEX idx_tenders_source_external_id ON tenders(source, external_id);
CREATE INDEX idx_tenders_source ON tenders(source);
CREATE INDEX idx_tenders_province ON tenders(province);
CREATE INDEX idx_tenders_naics ON tenders(naics);
CREATE INDEX idx_tenders_deadline ON tenders(deadline);
CREATE INDEX idx_tenders_scraped_at ON tenders(scraped_at);

-- Create awards table
CREATE TABLE awards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    vendor TEXT,
    value DECIMAL(15,2),
    award_date DATE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for awards table
CREATE UNIQUE INDEX idx_awards_source_external_id ON awards(source, external_id);
CREATE INDEX idx_awards_source ON awards(source);
CREATE INDEX idx_awards_vendor ON awards(vendor);
CREATE INDEX idx_awards_award_date ON awards(award_date);
CREATE INDEX idx_awards_value ON awards(value);

-- Create user bookmarks table
CREATE TABLE user_bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_bookmarks table
CREATE UNIQUE INDEX idx_user_bookmarks_user_tender ON user_bookmarks(user_id, tender_id);
CREATE INDEX idx_user_bookmarks_user_id ON user_bookmarks(user_id);
CREATE INDEX idx_user_bookmarks_tender_id ON user_bookmarks(tender_id);

-- Create vector embeddings table for similarity search
CREATE TABLE tender_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for tender_embeddings table
CREATE UNIQUE INDEX idx_tender_embeddings_tender_id ON tender_embeddings(tender_id);

-- Create award embeddings table
CREATE TABLE award_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    award_id UUID NOT NULL REFERENCES awards(id) ON DELETE CASCADE,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for award_embeddings table
CREATE UNIQUE INDEX idx_award_embeddings_award_id ON award_embeddings(award_id);

-- Create vector indexes for similarity search
CREATE INDEX ON tender_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON award_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_tenders_updated_at BEFORE UPDATE ON tenders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_awards_updated_at BEFORE UPDATE ON awards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for similarity search between tenders and awards
CREATE OR REPLACE FUNCTION find_similar_awards(tender_id UUID, limit_count INTEGER DEFAULT 5)
RETURNS TABLE (
    award_id UUID,
    similarity FLOAT,
    title TEXT,
    vendor TEXT,
    value DECIMAL(15,2),
    award_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        (te.embedding <=> ae.embedding) as similarity,
        a.title,
        a.vendor,
        a.value,
        a.award_date
    FROM tenders t
    JOIN tender_embeddings te ON t.id = te.tender_id
    CROSS JOIN award_embeddings ae
    JOIN awards a ON ae.award_id = a.id
    WHERE t.id = tender_id
    ORDER BY te.embedding <=> ae.embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Insert sample NAICS codes for onboarding
CREATE TABLE naics_codes (
    code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category TEXT
);

-- Sample NAICS codes for construction and related industries
INSERT INTO naics_codes (code, description, category) VALUES
('236110', 'Residential Building Construction', 'Construction'),
('236210', 'Industrial Building Construction', 'Construction'),
('236220', 'Commercial and Institutional Building Construction', 'Construction'),
('237110', 'Water and Sewer Line and Related Structures Construction', 'Construction'),
('237120', 'Oil and Gas Pipeline and Related Structures Construction', 'Construction'),
('237130', 'Power and Communication Line and Related Structures Construction', 'Construction'),
('237210', 'Land Subdivision', 'Construction'),
('237310', 'Highway, Street, and Bridge Construction', 'Construction'),
('237990', 'Other Heavy and Civil Engineering Construction', 'Construction'),
('238110', 'Poured Concrete Foundation and Structure Contractors', 'Construction'),
('238120', 'Structural Steel and Precast Concrete Contractors', 'Construction'),
('238130', 'Framing Contractors', 'Construction'),
('238140', 'Masonry Contractors', 'Construction'),
('238150', 'Glass and Glazing Contractors', 'Construction'),
('238160', 'Roofing Contractors', 'Construction'),
('238170', 'Siding Contractors', 'Construction'),
('238190', 'Other Foundation, Structure, and Building Exterior Contractors', 'Construction'),
('238210', 'Electrical Contractors and Other Wiring Installation Contractors', 'Construction'),
('238220', 'Plumbing, Heating, and Air-Conditioning Contractors', 'Construction'),
('238290', 'Other Building Equipment Contractors', 'Construction'),
('238310', 'Drywall and Insulation Contractors', 'Construction'),
('238320', 'Painting and Wall Covering Contractors', 'Construction'),
('238330', 'Flooring Contractors', 'Construction'),
('238340', 'Tile and Terrazzo Contractors', 'Construction'),
('238350', 'Finish Carpentry Contractors', 'Construction'),
('238390', 'Other Building Finishing Contractors', 'Construction'),
('238910', 'Site Preparation Contractors', 'Construction'),
('238990', 'All Other Specialty Trade Contractors', 'Construction'),
('332996', 'Fabricated Pipe and Pipe Fitting Manufacturing', 'Manufacturing'),
('332999', 'All Other Miscellaneous Fabricated Metal Product Manufacturing', 'Manufacturing'),
('333120', 'Construction Machinery Manufacturing', 'Manufacturing'),
('333922', 'Conveyor and Conveying Equipment Manufacturing', 'Manufacturing'),
('423320', 'Brick, Stone, and Related Construction Material Merchant Wholesalers', 'Wholesale'),
('423330', 'Roofing, Siding, and Insulation Material Merchant Wholesalers', 'Wholesale'),
('423390', 'Other Construction Material Merchant Wholesalers', 'Wholesale'),
('541330', 'Engineering Services', 'Professional Services'),
('541350', 'Building Inspection Services', 'Professional Services'),
('541360', 'Geophysical Surveying and Mapping Services', 'Professional Services'),
('541370', 'Surveying and Mapping (except Geophysical) Services', 'Professional Services'),
('541380', 'Testing Laboratories', 'Professional Services'),
('541611', 'Administrative Management and General Management Consulting Services', 'Professional Services'),
('541612', 'Human Resources Consulting Services', 'Professional Services'),
('541613', 'Marketing Consulting Services', 'Professional Services'),
('541614', 'Process, Physical Distribution, and Logistics Consulting Services', 'Professional Services'),
('541618', 'Other Management Consulting Services', 'Professional Services'),
('541620', 'Environmental Consulting Services', 'Professional Services'),
('541690', 'Other Scientific and Technical Consulting Services', 'Professional Services'),
('541990', 'All Other Professional, Scientific, and Technical Services', 'Professional Services'),
('561210', 'Facilities Support Services', 'Administrative Services'),
('561720', 'Janitorial Services', 'Administrative Services'),
('561730', 'Landscaping Services', 'Administrative Services'),
('561740', 'Carpet and Upholstery Cleaning Services', 'Administrative Services'),
('561790', 'Other Services to Buildings and Dwellings', 'Administrative Services'),
('562111', 'Solid Waste Collection', 'Waste Management'),
('562112', 'Hazardous Waste Collection', 'Waste Management'),
('562119', 'Other Waste Collection', 'Waste Management'),
('562211', 'Hazardous Waste Treatment and Disposal', 'Waste Management'),
('562212', 'Solid Waste Landfill', 'Waste Management'),
('562213', 'Solid Waste Combustors and Incinerators', 'Waste Management'),
('562219', 'Other Nonhazardous Waste Treatment and Disposal', 'Waste Management'),
('562910', 'Remediation Services', 'Waste Management'),
('562920', 'Materials Recovery Facilities', 'Waste Management'),
('562998', 'All Other Miscellaneous Waste Management Services', 'Waste Management'); 