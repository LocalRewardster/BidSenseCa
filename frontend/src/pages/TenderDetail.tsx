import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  ArrowLeftIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  MapPinIcon,
  BuildingOfficeIcon,
  DocumentTextIcon,
  LinkIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  TagIcon,
  UserIcon,
  EnvelopeIcon,
  PhoneIcon,
  HashtagIcon,
  ArrowTopRightOnSquareIcon,
  DocumentArrowDownIcon,
  LanguageIcon,
  TruckIcon,
  GlobeAltIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';
import { apiService, Tender, RelatedTender } from '../services/api';

export default function TenderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: tender, isLoading, error } = useQuery<Tender>({
    queryKey: ['tender', id],
    queryFn: () => apiService.getTender(id!),
    enabled: !!id,
  });

  // Fetch related tenders
  const { data: relatedTenders } = useQuery({
    queryKey: ['related-tenders', id],
    queryFn: () => apiService.getRelatedTenders(id!),
    enabled: !!id,
  });

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-CA', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString('en-CA', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const getStatusColor = (tender: Tender) => {
    if (!tender.closing_date) return 'bg-gray-100 text-gray-800';
    const closingDate = new Date(tender.closing_date);
    const now = new Date();
    if (closingDate < now) return 'bg-red-100 text-red-800';
    if (closingDate.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const getStatusText = (tender: Tender) => {
    if (!tender.closing_date) return 'No Deadline';
    const closingDate = new Date(tender.closing_date);
    const now = new Date();
    if (closingDate < now) return 'Closed';
    if (closingDate.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000) return 'Closing Soon';
    return 'Open';
  };

  const getDaysRemaining = (tender: Tender) => {
    if (!tender.closing_date) return null;
    const closingDate = new Date(tender.closing_date);
    const now = new Date();
    const diffTime = closingDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading tender details...</span>
        </div>
      </div>
    );
  }

  if (error || !tender) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <ExclamationTriangleIcon className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Tender Not Found</h2>
            <p className="text-gray-600 mb-4">The tender you're looking for doesn't exist or has been removed.</p>
            <button
              onClick={() => navigate('/tenders')}
              className="btn-primary"
            >
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              Back to Tenders
            </button>
          </div>
        </div>
      </div>
    );
  }

  const daysRemaining = getDaysRemaining(tender);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/tenders')}
            className="btn-secondary"
          >
            <ArrowLeftIcon className="w-4 h-4 mr-2" />
            Back
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tender Details</h1>
            <p className="text-gray-600">View detailed information about this tender</p>
          </div>
        </div>
        <div className="flex space-x-2">
          {tender.url && (
            <button
              onClick={() => window.open(tender.url, '_blank')}
              className="btn-primary"
            >
              <LinkIcon className="w-4 h-4 mr-2" />
              View Original
            </button>
          )}
        </div>
      </div>

      {/* Status Banner */}
      <div className={`card p-4 ${getStatusColor(tender).replace('text-', 'border-').replace('bg-', 'border-')}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <ClockIcon className="w-5 h-5 mr-2" />
            <span className="font-medium">{getStatusText(tender)}</span>
          </div>
          {daysRemaining !== null && (
            <div className="text-sm">
              {daysRemaining > 0 ? (
                <span>{daysRemaining} days remaining</span>
              ) : daysRemaining === 0 ? (
                <span>Closes today</span>
              ) : (
                <span>Closed {Math.abs(daysRemaining)} days ago</span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Title and Description */}
          <div className="card">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">{tender.title}</h2>
                {tender.category && (
                  <span className="inline-block px-3 py-1 text-sm font-semibold rounded-full bg-blue-100 text-blue-800">
                    {tender.category}
                  </span>
                )}
              </div>
              {tender.description && (
                <div className="prose max-w-none">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{tender.description}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Key Information */}
          <div className="card">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center space-x-3">
                  <BuildingOfficeIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Organization</p>
                    <p className="text-gray-900">{tender.organization}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <MapPinIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Location</p>
                    <p className="text-gray-900">{tender.location || 'N/A'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <CurrencyDollarIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Contract Value</p>
                    <p className="text-gray-900">{tender.contract_value || 'N/A'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <CalendarIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Closing Date</p>
                    <p className="text-gray-900">{formatDate(tender.closing_date)}</p>
                  </div>
                </div>
                {tender.reference && (
                  <div className="flex items-center space-x-3">
                    <HashtagIcon className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-500">Reference</p>
                      <p className="text-gray-900">{tender.reference}</p>
                    </div>
                  </div>
                )}
                <div className="flex items-center space-x-3">
                  <TagIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Source</p>
                    <p className="text-gray-900 capitalize">{tender.source_name}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Summary Information */}
          {(tender.notice_type || tender.languages || tender.delivery_regions || tender.opportunity_region || tender.contract_duration || tender.procurement_method || tender.selection_criteria || tender.commodity_unspsc) && (
            <div className="card">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {tender.notice_type && (
                    <div className="flex items-center space-x-3">
                      <DocumentTextIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Notice Type</p>
                        <p className="text-gray-900">{tender.notice_type}</p>
                      </div>
                    </div>
                  )}
                  {tender.languages && (
                    <div className="flex items-center space-x-3">
                      <LanguageIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Languages</p>
                        <p className="text-gray-900">{tender.languages}</p>
                      </div>
                    </div>
                  )}
                  {tender.delivery_regions && (
                    <div className="flex items-center space-x-3">
                      <TruckIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Delivery Regions</p>
                        <p className="text-gray-900">{tender.delivery_regions}</p>
                      </div>
                    </div>
                  )}
                  {tender.opportunity_region && (
                    <div className="flex items-center space-x-3">
                      <GlobeAltIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Opportunity Region</p>
                        <p className="text-gray-900">{tender.opportunity_region}</p>
                      </div>
                    </div>
                  )}
                  {tender.contract_duration && (
                    <div className="flex items-center space-x-3">
                      <ClockIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Contract Duration</p>
                        <p className="text-gray-900">{tender.contract_duration}</p>
                      </div>
                    </div>
                  )}
                  {tender.procurement_method && (
                    <div className="flex items-center space-x-3">
                      <ClipboardDocumentListIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Procurement Method</p>
                        <p className="text-gray-900">{tender.procurement_method}</p>
                      </div>
                    </div>
                  )}
                  {tender.selection_criteria && (
                    <div className="flex items-center space-x-3">
                      <CheckCircleIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Selection Criteria</p>
                        <p className="text-gray-900">{tender.selection_criteria}</p>
                      </div>
                    </div>
                  )}
                  {tender.commodity_unspsc && (
                    <div className="flex items-center space-x-3 md:col-span-2">
                      <CubeIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Commodity (UNSPSC)</p>
                        <p className="text-gray-900">{tender.commodity_unspsc}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Contact Information */}
          {(tender.contact_name || tender.contact_email || tender.contact_phone) && (
            <div className="card">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {tender.contact_name && (
                    <div className="flex items-center space-x-3">
                      <UserIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Contact Person</p>
                        <p className="text-gray-900">{tender.contact_name}</p>
                      </div>
                    </div>
                  )}
                  {tender.contact_email && (
                    <div className="flex items-center space-x-3">
                      <EnvelopeIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Email</p>
                        <a href={`mailto:${tender.contact_email}`} className="text-blue-600 hover:text-blue-800">
                          {tender.contact_email}
                        </a>
                      </div>
                    </div>
                  )}
                  {tender.contact_phone && (
                    <div className="flex items-center space-x-3">
                      <PhoneIcon className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-500">Phone</p>
                        <a href={`tel:${tender.contact_phone}`} className="text-blue-600 hover:text-blue-800">
                          {tender.contact_phone}
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Documents */}
          {tender.documents_urls && tender.documents_urls.length > 0 && (
            <div className="card">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Documents</h3>
                <div className="space-y-3">
                  {tender.documents_urls.map((url, index) => {
                    const fileName = url.split('/').pop() || `Document ${index + 1}`;
                    const fileExtension = fileName.split('.').pop()?.toLowerCase();
                    
                    return (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <DocumentArrowDownIcon className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{fileName}</p>
                            <p className="text-sm text-gray-500 capitalize">{fileExtension} file</p>
                          </div>
                        </div>
                        <button
                          onClick={() => window.open(url, '_blank')}
                          className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                          title="Download document"
                        >
                          <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                        </button>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Related Tenders */}
          {relatedTenders?.success && relatedTenders.data.length > 0 && (
            <div className="card">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Related Tenders</h3>
                <div className="space-y-3">
                  {relatedTenders.data.map((relatedTender) => (
                    <motion.div
                      key={relatedTender.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/tenders/${relatedTender.id}`)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 line-clamp-2">{relatedTender.title}</h4>
                          <p className="text-sm text-gray-600 mt-1">{relatedTender.organization}</p>
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span className="capitalize">{relatedTender.source_name}</span>
                            {relatedTender.closing_date && (
                              <span>Closes: {formatDate(relatedTender.closing_date)}</span>
                            )}
                          </div>
                        </div>
                        <LinkIcon className="w-4 h-4 text-gray-400 ml-2" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Metadata */}
          <div className="card">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h3>
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-500">Added to Database</p>
                  <p className="text-sm text-gray-900">{formatDateTime(tender.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Last Updated</p>
                  <p className="text-sm text-gray-900">{formatDateTime(tender.updated_at)}</p>
                </div>
                {tender.external_id && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">External ID</p>
                    <p className="text-sm text-gray-900 font-mono">{tender.external_id}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={() => navigate('/tenders')}
                  className="w-full btn-secondary text-left"
                >
                  <DocumentTextIcon className="w-4 h-4 mr-2" />
                  View All Tenders
                </button>
                {tender.original_url && (
                  <button
                    onClick={() => window.open(tender.original_url, '_blank')}
                    className="w-full btn-primary text-left"
                  >
                    <ArrowTopRightOnSquareIcon className="w-4 h-4 mr-2" />
                    View Original Notice
                  </button>
                )}
                {tender.url && tender.url !== tender.original_url && (
                  <button
                    onClick={() => window.open(tender.url, '_blank')}
                    className="w-full btn-secondary text-left"
                  >
                    <LinkIcon className="w-4 h-4 mr-2" />
                    View Source Page
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
} 