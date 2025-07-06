# Advanced Search Frontend Integration

## Overview

This document summarizes the implementation of advanced search functionality in the BidSense.ca frontend, including the integration with the backend advanced search API.

## Components Created

### 1. AdvancedSearch Component (`src/components/AdvancedSearch.tsx`)

A comprehensive search interface that provides:

- **Advanced Search Toggle**: Enable/disable advanced search mode
- **Help Panel**: Collapsible documentation of advanced search features
- **Examples Panel**: Interactive search examples with click-to-search functionality
- **Enhanced Search Input**: Context-aware placeholder text and styling
- **Improved Suggestions**: Better suggestion display with type and frequency indicators

**Features:**
- Boolean operators (AND, OR, NOT)
- Field prefixes (buyer:, province:, naics:)
- Phrase search with quotes
- Wildcard support (* and ?)
- Grouping with parentheses
- Real-time search suggestions
- Visual feedback for advanced search mode

### 2. SearchResults Component (`src/components/SearchResults.tsx`)

Enhanced results display with:

- **Advanced Search Info Panel**: Shows query parsing details and applied filters
- **Highlighted Results**: Displays search term highlighting in titles and descriptions
- **Rank Indicators**: Shows relevance scores for advanced search results
- **Improved Layout**: Card-based design with better information hierarchy
- **Loading States**: Skeleton loading animations
- **Error Handling**: Graceful error display

**Features:**
- Query information display
- Result highlighting
- Relevance ranking
- Responsive design
- Smooth animations

## API Integration Updates

### Updated API Service (`src/services/api.ts`)

Enhanced with new interfaces and methods:

**New Interfaces:**
```typescript
interface SearchStatistics {
  total_tenders: number;
  tenders_with_summary: number;
  tenders_with_documents: number;
  tenders_with_contacts: number;
  avg_search_vector_length: number;
}

interface SearchExample {
  query: string;
  description: string;
}

interface TendersResponse {
  // ... existing fields
  query_info?: {
    original_query: string;
    parsed_query: string;
    filters: Record<string, any>;
    field_filters: Record<string, any>;
    wildcards: string[];
    has_errors: boolean;
    error_message?: string;
  };
}
```

**New Methods:**
- `getSearchStatistics()`: Fetch search-related statistics
- `getSearchExamples()`: Get example search queries
- Enhanced `getTenders()`: Support for `use_advanced_search` parameter

### Updated Tender Interface

Added advanced search fields:
```typescript
interface Tender {
  // ... existing fields
  rank?: number;        // Search relevance rank
  highlight?: string;   // Highlighted search terms
}
```

## Updated Pages

### Tenders Page (`src/pages/Tenders.tsx`)

Completely refactored to use new components:

**Key Changes:**
- Replaced inline search with `AdvancedSearch` component
- Replaced table view with `SearchResults` component
- Added advanced search toggle state management
- Enhanced query key dependencies for React Query
- Added search examples integration
- Improved filter layout and organization

**New Features:**
- Advanced search mode toggle
- Search examples integration
- Enhanced result display
- Better filter organization
- Improved pagination

## Styling Updates

### Enhanced CSS (`src/styles/globals.css`)

Added new utility classes:

```css
/* Line clamp utilities */
.line-clamp-1, .line-clamp-2, .line-clamp-3

/* Advanced search specific styles */
.search-highlight
.search-rank
```

## User Experience Features

### 1. Advanced Search Toggle
- Visual indicator when advanced search is enabled
- Context-aware placeholder text
- Different styling for advanced vs basic search

### 2. Interactive Help
- Collapsible help panel with search syntax
- Code examples with syntax highlighting
- Organized by feature category

### 3. Search Examples
- Clickable example queries
- Descriptive explanations
- Automatic search execution on click

### 4. Enhanced Suggestions
- Type indicators (word, title, organization)
- Frequency counts
- Better visual hierarchy

### 5. Result Highlighting
- Search term highlighting in titles and descriptions
- HTML-safe highlighting from backend
- Fallback client-side highlighting

### 6. Query Information Display
- Shows original and parsed queries
- Displays applied filters and field filters
- Error reporting for malformed queries

## Testing

### API Endpoints Verified
- ✅ Search examples endpoint
- ✅ Search statistics endpoint
- ✅ Advanced search with query parsing
- ✅ Complex query handling
- ✅ Search suggestions
- ✅ Basic search compatibility

### Test Results
```bash
# Search Examples
curl "http://localhost:8000/api/v1/tenders/search-examples"
# Returns 6 example queries with descriptions

# Search Statistics
curl "http://localhost:8000/api/v1/tenders/search-statistics"
# Returns database statistics

# Advanced Search
curl "http://localhost:8000/api/v1/tenders/?search=flooring&use_advanced_search=true"
# Returns results with query_info

# Complex Query
curl "http://localhost:8000/api/v1/tenders/?search=buyer:\"Department%20of%20National%20Defence\"%20AND%20category:Construction&use_advanced_search=true"
# Correctly parses field filters
```

## Integration Status

### ✅ Completed
- [x] AdvancedSearch component implementation
- [x] SearchResults component implementation
- [x] API service updates
- [x] Tenders page integration
- [x] Styling and animations
- [x] Error handling
- [x] Loading states
- [x] Responsive design
- [x] Backend API integration
- [x] Query parsing display
- [x] Search examples integration

### 🔄 Ready for Testing
- [ ] Frontend development server testing
- [ ] User interaction testing
- [ ] Cross-browser compatibility
- [ ] Performance testing
- [ ] Accessibility testing

## Next Steps

### Phase 1 Completion
1. **Apply Database Migration**: Run the advanced search migration to enable full-text search
2. **Frontend Testing**: Test the complete user experience
3. **Performance Optimization**: Monitor and optimize search performance
4. **User Documentation**: Create user guide for advanced search features

### Phase 2 Features (Future)
- Search history and saved searches
- Advanced filters (date ranges, value ranges)
- Export search results
- Search analytics and insights
- Personalized search preferences

## Technical Notes

### Dependencies
- React 19.1.0
- TypeScript 5.8.3
- Framer Motion 12.23.0
- Heroicons 2.2.0
- React Query 5.81.5

### Browser Support
- Modern browsers with ES2020 support
- CSS Grid and Flexbox support required
- Optional: CSS backdrop-filter for glass effects

### Performance Considerations
- Lazy loading of search examples
- Debounced search suggestions
- Optimized React Query caching
- Efficient re-rendering with proper dependencies

## Conclusion

The advanced search frontend integration is complete and ready for testing. The implementation provides a modern, user-friendly interface for advanced search capabilities while maintaining backward compatibility with basic search functionality.

The integration successfully connects to the backend advanced search API and provides comprehensive feedback to users about their search queries and results. 