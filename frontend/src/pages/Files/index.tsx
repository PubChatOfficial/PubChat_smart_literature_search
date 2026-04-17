import React, { useState, useEffect } from 'react';
import { useTheme } from '@/utils/ThemeContext';
import { useToast } from '@/components/Toast/ToastContext';
import { ConfirmModal } from '@/components/PopUpWindows/ConfirmWindow';
import { CaretLeft, CaretRight, DownloadSimple, Trash, FileText, Clock, HardDrive, Package } from '@phosphor-icons/react';
import { getUserDocuments, deleteDocument, downloadSearchResult } from '@/api/Search/searchApi';
import { SearchDocument } from '@/interface/search/searchInterface';
import './RecentFiles.css';

export const RecentFiles: React.FC = () => {
  const { theme } = useTheme();
  const { showSuccess, showError } = useToast();
  // const [currentType, setCurrentType] = useState<'search' | 'review' | 'search-review'>('search'); // Tabs temporarily disabled or unused for now
  const [currentPage, setCurrentPage] = useState(1);
  const [files, setFiles] = useState<SearchDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<string | null>(null);
  const itemsPerPage = 5;

  const translations = {
    en: {
      taskType: 'Task Type',
      typeSearch: 'Literature Search',
      typeReview: 'Literature Review',
      typeSearchReview: 'Search & Review',
      files: 'Files',
      download: 'Download',
      delete: 'Delete',
      time: 'Time',
      size: 'Size',
      confirmDelete: 'Are you sure you want to delete this file?',
      deleteSuccess: 'File deleted successfully!',
      fetchError: 'Failed to fetch documents',
      deleteError: 'Failed to delete file'
    },
    zh: {
      taskType: '任务类型',
      typeSearch: '文献检索',
      typeReview: '文献综述',
      typeSearchReview: '检索与综述',
      files: '文件列表',
      download: '下载',
      delete: '删除',
      time: '时间',
      size: '大小',
      confirmDelete: '确定要删除此文件吗？',
      deleteSuccess: '文件删除成功！',
      fetchError: '获取文件列表失败',
      deleteError: '删除文件失败'
    }
  };

  const t = translations[theme.language];

  // Fetch documents on mount
  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const res = await getUserDocuments();
      if (res.success && res.data) {
        setFiles(res.data);
      } else {
        showError(typeof res.message === 'string' ? res.message : res.message?.[theme.language] || t.fetchError);
      }
    } catch (error) {
      console.error(error)
      showError(t.fetchError);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [theme.language]);

  const handleDownload = (downloadLink: string) => {
    downloadSearchResult(downloadLink);
  };

  const handleDeleteClick = (fileId: string) => {
    setFileToDelete(fileId);
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (fileToDelete !== null) {
      const res = await deleteDocument(fileToDelete);
      if (res.success) {
        showSuccess(t.deleteSuccess);
        // Refresh list
        setFiles(prev => prev.filter(f => f.id !== fileToDelete));
      } else {
        showError(typeof res.message === 'string' ? res.message : res.message?.[theme.language] || t.deleteError);
      }
      setShowDeleteModal(false);
      setFileToDelete(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteModal(false);
    setFileToDelete(null);
  };

  const totalPages = Math.ceil(files.length / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const pageFiles = files.slice(startIndex, endIndex);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  // Detect mobile viewport
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth <= 480;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 480);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const formatTime = (isoString: string) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString(theme.language === 'en' ? 'en-US' : 'zh-CN');
  }

  return (
    <div className="recent-files-content">
      {/* Files List */}
      <div className="files-list-card">
        {isMobile ? (
          /* Mobile layout: 2 rows */
          <div className="files-list-header files-list-header-mobile">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <span className="files-count">
                {theme.language === 'en' ? 'Available Documents' : '可用文档'}
              </span>
              <span className="files-number">
                {files.length} {theme.language === 'en' ? 'files' : '个文件'}
              </span>
            </div>
          </div>
        ) : (
          /* Desktop layout: original */
          <div className="files-list-header" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span className="files-count">
                {theme.language === 'en' ? 'Available Documents' : '可用文档'}
              </span>
            </div>
            <span className="files-number">
              {files.length} {theme.language === 'en' ? 'files' : '个文件'}
            </span>
          </div>
        )}
        <div className="files-list">
          {isLoading ? (
            <div className="loading-state" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              {theme.language === 'en' ? 'Loading...' : '加载中...'}
            </div>
          ) : pageFiles.length > 0 ? (
            pageFiles.map((file) => (
              <div key={file.id} className="file-item" data-id={file.id}>
                <div className="file-icon-wrapper">
                  <Package size={24} weight="fill" />
                </div>
                <div className="file-main-info">
                  <div className="file-name">{file.user_query}</div>
                  <div className="file-meta">
                    <span className="meta-item">
                      <Clock size={14} weight="regular" />
                      {formatTime(file.created_time)}
                    </span>
                    <span className="meta-item">
                      <HardDrive size={14} weight="regular" />
                      {file.size ? `${Number(file.size).toFixed(2)} MB` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="file-actions">
                  <button
                    className="action-btn download-btn"
                    onClick={() => handleDownload(file.download_link)}
                    title={t.download}
                  >
                    <DownloadSimple size={18} weight="regular" />
                  </button>
                  <button
                    className="action-btn delete-btn"
                    onClick={() => handleDeleteClick(file.id)}
                    title={t.delete}
                  >
                    <Trash size={18} weight="regular" />
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <FileText size={48} weight="regular" />
              <p>{theme.language === 'en' ? 'No files found' : '暂无文件'}</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {files.length > 0 && (
          <div className="pagination">
            <button
              className="page-btn prev-btn"
              onClick={handlePrevPage}
              disabled={currentPage <= 1}
              title={theme.language === 'en' ? 'Previous page' : '上一页'}
            >
              <CaretLeft size={20} weight="bold" />
            </button>
            <span className="page-info">{currentPage}/{totalPages}</span>
            <button
              className="page-btn next-btn"
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              title={theme.language === 'en' ? 'Next page' : '下一页'}
            >
              <CaretRight size={20} weight="bold" />
            </button>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        title={theme.language === 'en' ? 'Delete File' : '删除文件'}
        message={t.confirmDelete}
        confirmText={theme.language === 'en' ? 'Delete' : '删除'}
        cancelText={theme.language === 'en' ? 'Cancel' : '取消'}
        confirmButtonColor="red"
      />
    </div >
  );
};

