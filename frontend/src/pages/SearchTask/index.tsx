import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '@/utils/ThemeContext';
import { useOutputLanguage, OUTPUT_LANGUAGES } from '@/utils/useOutputLanguage';
import { Cookies } from '@/utils/cookies';

import { ArrowUp, CaretUp, CaretDown, ArrowClockwise } from '@phosphor-icons/react';
import { createSearchTask } from '@/api/Search/searchApi';
import { SearchTaskRequest } from '@/interface/search/searchInterface';
import { motion, AnimatePresence } from 'framer-motion';
import './SearchTask.css';
import '@/styles/MobileOutputLanguage.css'; // Mobile layout for output language

import { useToast } from '@/components/Toast/ToastContext';

const AI_MODEL_CUSTOM = '__custom__';
const DEFAULT_AI_MODEL = 'gemini-2.5-pro';

const AI_MODEL_OPTIONS: ReadonlyArray<{
  value: string;
  labelEn: string;
  labelZh: string;
}> = [
  // { value: 'gpt-4o', labelEn: 'OpenAI · gpt-4o', labelZh: 'OpenAI · gpt-4o' },
  // { value: 'gpt-4o-mini', labelEn: 'OpenAI · gpt-4o-mini', labelZh: 'OpenAI · gpt-4o-mini' },
  // { value: 'gpt-4-turbo', labelEn: 'OpenAI · gpt-4-turbo', labelZh: 'OpenAI · gpt-4-turbo' },
  { value: 'google', labelEn: 'Google · gemini', labelZh: 'Google · gemini' },
  // { value: 'deepseek-chat', labelEn: 'DeepSeek · deepseek-chat', labelZh: 'DeepSeek · deepseek-chat' },
  // {
  //   value: 'claude-3-5-sonnet-20241022',
  //   labelEn: 'Anthropic · claude-3-5-sonnet',
  //   labelZh: 'Anthropic · claude-3-5-sonnet',
  // },
  // { value: AI_MODEL_CUSTOM, labelEn: 'Custom…', labelZh: '自定义…' },
];

export const LiteratureSearchTask: React.FC = () => {
  const { theme } = useTheme();
  const { showSuccess, showError } = useToast();
  const location = useLocation();
  const navigate = useNavigate();
  const [showContent, setShowContent] = useState(false);

  // Search query state - 从路由 state 中获取初始值
  const [searchQuery, setSearchQuery] = useState(() => {
    const state = location.state as { query?: string } | null;
    return state?.query || '';
  });

  // Check for existing search task
  useEffect(() => {
    // Check if we have a task ID in cookies
    const existingTaskId = Cookies.getSearchTaskId();
    if (existingTaskId?.display) {
      // If display true redirect to results
      navigate('/search/result');
    }
  }, [navigate]);

  // 默认延迟显示内容，等待输入框过渡动画开始
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowContent(true);
    }, 150);
    return () => clearTimeout(timer);
  }, []);

  // Output language state - 使用自定义 hook
  const [outputLanguage, setOutputLanguage] = useOutputLanguage();

  // PubMed limits state
  const [pubmedLimits, setPubmedLimits] = useState(() => {
    const saved = Cookies.getPubMedLimits<{
      time: string;
      affiliation: string;
      journal: string;
      author: string;
      firstAuthor: string;
      lastAuthor: string;
      selfFilter: string;
    }>();
    return saved || {
      time: '',
      affiliation: '',
      journal: '',
      author: '',
      firstAuthor: '',
      lastAuthor: '',
      selfFilter: '',
    };
  });

  // Journal limits state - Range sliders
  const [impactFactor, setImpactFactor] = useState(() => {
    const saved = Cookies.getJournalLimits<{ impactFactor: { left: number; right: number } }>();
    return saved?.impactFactor || { left: 0, right: 100 };
  });
  const [jcrZone, setJcrZone] = useState(() => {
    const saved = Cookies.getJournalLimits<{ jcrZone: { left: number; right: number } }>();
    return saved?.jcrZone || { left: 1, right: 4 };
  });
  const [casZone, setCasZone] = useState(() => {
    const saved = Cookies.getJournalLimits<{ casZone: { left: number; right: number } }>();
    return saved?.casZone || { left: 1, right: 4 };
  });

  // Search settings state
  const [maxRounds, setMaxRounds] = useState<number | string>(() => {
    const saved = Cookies.getSearchSettings<{ maxRounds: number }>();
    return saved?.maxRounds || 5;
  });
  const [autoStopArticles, setAutoStopArticles] = useState<number | string>(() => {
    const saved = Cookies.getSearchSettings<{ autoStopArticles: number }>();
    return saved?.autoStopArticles || 20;
  });

  const [aiModelPreset, setAiModelPreset] = useState(() => {
    const saved = Cookies.getAiApiModel();
    const savedPreset = saved?.preset;
    const hasSaved = !!savedPreset && AI_MODEL_OPTIONS.some((opt) => opt.value === savedPreset);
    return hasSaved ? (savedPreset as string) : DEFAULT_AI_MODEL;
  });
  const [aiCustomModel, setAiCustomModel] = useState(() => {
    const saved = Cookies.getAiApiModel();
    return saved?.customModel || '';
  });
  const [aiApiKey, setAiApiKey] = useState(() => {
    const saved = Cookies.getAiApiModel();
    return saved?.apiKey || '';
  });

  const [aiModelMenuOpen, setAiModelMenuOpen] = useState(false);
  const aiModelDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aiModelMenuOpen) return;
    const onDocPointerDown = (e: PointerEvent) => {
      const el = aiModelDropdownRef.current;
      if (el && !el.contains(e.target as Node)) {
        setAiModelMenuOpen(false);
      }
    };
    document.addEventListener('pointerdown', onDocPointerDown);
    return () => document.removeEventListener('pointerdown', onDocPointerDown);
  }, [aiModelMenuOpen]);

  useEffect(() => {
    if (!aiModelMenuOpen) return;
    const onScrollOrResize = () => setAiModelMenuOpen(false);
    window.addEventListener('resize', onScrollOrResize);
    const scrollEl = document.querySelector('.content-scroll');
    scrollEl?.addEventListener('scroll', onScrollOrResize, { passive: true });
    return () => {
      window.removeEventListener('resize', onScrollOrResize);
      scrollEl?.removeEventListener('scroll', onScrollOrResize);
    };
  }, [aiModelMenuOpen]);

  // Persist PubMed limits
  useEffect(() => {
    Cookies.setPubMedLimits(pubmedLimits);
  }, [pubmedLimits]);

  // Persist Journal limits
  useEffect(() => {
    Cookies.setJournalLimits({ impactFactor, jcrZone, casZone });
  }, [impactFactor, jcrZone, casZone]);

  // Persist Search settings
  useEffect(() => {
    Cookies.setSearchSettings({ maxRounds, autoStopArticles });
  }, [maxRounds, autoStopArticles]);

  useEffect(() => {
    Cookies.setAiApiModel({ preset: aiModelPreset, customModel: aiCustomModel, apiKey: aiApiKey });
  }, [aiModelPreset, aiCustomModel, aiApiKey]);

  // Refs for range sliders
  const ifLeftRef = useRef<HTMLInputElement>(null);
  const ifRightRef = useRef<HTMLInputElement>(null);
  const jcrLeftRef = useRef<HTMLInputElement>(null);
  const jcrRightRef = useRef<HTMLInputElement>(null);
  const casLeftRef = useRef<HTMLInputElement>(null);
  const casRightRef = useRef<HTMLInputElement>(null);

  // Impact Factor slider handlers
  const updateImpactFactor = (value: number, isLeft: boolean) => {
    let left = isLeft ? value : impactFactor.left;
    let right = isLeft ? impactFactor.right : value;

    if (left > right) {
      if (isLeft) {
        left = right;
      } else {
        right = left;
      }
    }
    setImpactFactor({ left, right });
  };

  const getImpactFactorDisplay = () => {
    const leftVal = impactFactor.left === 0 ? '0' : Math.round(impactFactor.left / 2);
    const rightVal = impactFactor.right === 100 ? '+∞' : Math.round(impactFactor.right / 2);
    return `${leftVal}~${rightVal}`;
  };

  // JCR Zone slider handlers
  const updateJcrZone = (value: number, isLeft: boolean) => {
    let left = isLeft ? value : jcrZone.left;
    let right = isLeft ? jcrZone.right : value;

    if (left > right) {
      if (isLeft) {
        left = right;
      } else {
        right = left;
      }
    }
    setJcrZone({ left, right });
  };

  const getJcrZoneDisplay = () => {
    return `Q${jcrZone.left}~Q${jcrZone.right}`;
  };

  // CAS Zone slider handlers
  const updateCasZone = (value: number, isLeft: boolean) => {
    let left = isLeft ? value : casZone.left;
    let right = isLeft ? casZone.right : value;

    if (left > right) {
      if (isLeft) {
        left = right;
      } else {
        right = left;
      }
    }
    setCasZone({ left, right });
  };

  const getCasZoneDisplay = () => {
    return `Z${casZone.left}~Z${casZone.right}`;
  };

  // Calculate track positions for range sliders
  const getIfTrackStyle = () => {
    const leftPercent = impactFactor.left;
    const rightPercent = 100 - impactFactor.right;
    return { left: `${leftPercent}%`, right: `${rightPercent}%` };
  };

  const getJcrTrackStyle = () => {
    const leftPercent = ((jcrZone.left - 1) / 3) * 100;
    const rightPercent = ((4 - jcrZone.right) / 3) * 100;
    return { left: `${leftPercent}%`, right: `${rightPercent}%` };
  };

  const getCasTrackStyle = () => {
    const leftPercent = ((casZone.left - 1) / 3) * 100;
    const rightPercent = ((4 - casZone.right) / 3) * 100;
    return { left: `${leftPercent}%`, right: `${rightPercent}%` };
  };

  // Number input handlers
  const handleMaxRoundsChange = (delta: number) => {
    setMaxRounds(prev => {
      const val = typeof prev === 'string' ? (parseInt(prev) || 0) : prev;
      const newVal = Math.max(1, val + delta);
      return Math.min(newVal, 50); // Max 50
    });
  };

  const handleAutoStopArticlesChange = (delta: number) => {
    setAutoStopArticles(prev => {
      const val = typeof prev === 'string' ? (parseInt(prev) || 0) : prev;
      const newVal = Math.max(1, val + delta);
      return Math.min(newVal, 500); // Max 500
    });
  };

  // Handle search
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      showError(theme.language === 'en' ? 'Please enter your research question' : '请输入您的研究问题');
      return;
    }

    if (aiModelPreset === AI_MODEL_CUSTOM && !aiCustomModel.trim()) {
      showError(
        theme.language === 'en' ? 'Please enter a custom model id' : '请选择「自定义模型」时请填写模型名称或 ID'
      );
      return;
    }

    const resolvedModel =
      aiModelPreset === AI_MODEL_CUSTOM ? aiCustomModel.trim() : aiModelPreset;

    if (!resolvedModel) {
      showError(theme.language === 'en' ? 'Please select an AI model' : '请先选择 AI 模型');
      return;
    }

    if (!aiApiKey.trim()) {
      showError(theme.language === 'en' ? 'Please configure your AI API key' : '请先配置 AI 接口的 API 密钥');
      return;
    }

    // Format Impact Factor
    let ifString = '';
    const ifLeft = impactFactor.left === 0 ? 0 : Math.round(impactFactor.left / 2);
    const ifRight = impactFactor.right === 100 ? null : Math.round(impactFactor.right / 2);

    if (ifRight === null) {
      // Max is Infinity
      if (ifLeft > 0) {
        ifString = `>=${ifLeft}`;
      } else {
        ifString = ''; // 0 to Infinity -> No filter
      }
    } else {
      // Max is finite
      if (ifLeft === 0) {
        ifString = `<=${ifRight}`;
      } else {
        ifString = `${ifLeft}-${ifRight}`;
      }
    }

    const requestData: SearchTaskRequest = {
      user_query: searchQuery,
      outputlanguage: outputLanguage,
      search_settings: {
        max_refinement_attempts: Number(maxRounds) || 5, // Ensure number
        min_study_threshold: Number(autoStopArticles) || 20 // Ensure number
      },
      search_filters: {
        time: pubmedLimits.time,
        author: pubmedLimits.author,
        first_author: pubmedLimits.firstAuthor,
        last_author: pubmedLimits.lastAuthor,
        affiliation: pubmedLimits.affiliation,
        journal: pubmedLimits.journal,
        custom: pubmedLimits.selfFilter
      },
      journal_filters: {
        impact_factor: ifString,
        jcr_zone: `Q${jcrZone.left}-Q${jcrZone.right}`,
        cas_zone: `${casZone.left}-${casZone.right}`
      }
    };

    // Always send model + api (also keep legacy keys for backend compatibility)
    requestData.llm_config = {
      model: resolvedModel,
      api: [aiApiKey.trim()],
    };

    try {
      // Call API to start task
      const response = await createSearchTask(requestData);

      if (response.success && response.data) {
        // Save task_id to cookies
        if ((response.data as any).search_task_id) {
          // Set cookie to expire in 30 minutes (30 / (24 * 60) days)
          Cookies.setSearchTaskId({ taskId: (response.data as any).search_task_id, display: true }, { expires: 30 / 1440 });
        }
        showSuccess(theme.language === 'en' ? response.message.en : response.message.zh);

        // Navigate to search result page with task_id or response data
        navigate('/search/result');
      } else {
        // Handle error (using toast ideally, need to import useToast if available)
        showError(theme.language === 'en' ? response.message.en : response.message.zh);
      }
    } catch (error) {
      console.error('Error in handleSearch:', error);
      showError(theme.language === 'en' ? 'Search failed, please try again.' : '搜索失败，请重试。');
    }
  };

  // Reset Journal Limits
  const resetJournalLimits = () => {
    setImpactFactor({ left: 0, right: 100 });
    setJcrZone({ left: 1, right: 4 });
    setCasZone({ left: 1, right: 4 });

    // Update refs
    if (ifLeftRef.current) ifLeftRef.current.value = '0';
    if (ifRightRef.current) ifRightRef.current.value = '100';
    if (jcrLeftRef.current) jcrLeftRef.current.value = '1';
    if (jcrRightRef.current) jcrRightRef.current.value = '4';
    if (casLeftRef.current) casLeftRef.current.value = '1';
    if (casRightRef.current) casRightRef.current.value = '4';
  };

  // Reset PubMed Limits
  const resetPubMedLimits = () => {
    setPubmedLimits({
      time: '',
      affiliation: '',
      journal: '',
      author: '',
      firstAuthor: '',
      lastAuthor: '',
      selfFilter: '',
    });
  };

  // Reset Search Settings
  const resetSearchSettings = () => {
    setMaxRounds(5);
    setAutoStopArticles(20);
  };

  const resetAiApiConfig = () => {
    setAiModelPreset(DEFAULT_AI_MODEL);
    setAiCustomModel('');
    setAiApiKey('');
    Cookies.setAiApiModel({ preset: DEFAULT_AI_MODEL, customModel: '', apiKey: '' });
  };

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-focus the textarea when the component mounts
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  return (
    <div className="task-page-container">
      {/* Fixed Search Area */}
      <div className="fixed-search-area">
        <div className="content-wrapper">
          {/* Search Setting */}
          <section className="form-section search-section-wrapper">
            <div className="section-header">
              <span className="dot"></span>
              <h3>{theme.language === 'en' ? 'Search Question' : '检索问题'}
                <span className="required-dot" aria-hidden="true">*</span>
              </h3>
              
            </div>
            <motion.div
              layoutId="search-input-container"
              layout={false}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
              }}
              onAnimationComplete={() => {
                setShowContent(true);
              }}
              className="search-box-container"
            >
              <textarea
                ref={textareaRef}
                placeholder={theme.language === 'en' ? 'Enter your medical research question (Supports natural language description)...' : '请输入您的医学研究问题（支持自然语言描述）...'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSearch();
                  }
                }}
              />
              <button className="search-btn" onClick={handleSearch} title="Search">
                <ArrowUp weight="bold" size={20} />
              </button>
            </motion.div>
            <p className="search-note">{theme.language === 'en' ? 'Supports multiple language output, system will automatically generate professional PubMed search terms.' : '支持多语言输出，系统将基于您的问题自动构建符合PubMed规范的专业检索式。'}</p>
          </section>
        </div>
      </div>

      {/* Scrollable Content Area */}
      <AnimatePresence>
        {showContent && (
          <motion.div
            className="content-scroll"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="content-wrapper">
              <section className="form-section section-box ai-api-config-section">
                <div className="section-header">
                  <h3>
                    {theme.language === 'en' ? 'AI API' : 'AI 接口配置'}
                    <span className="required-dot" aria-hidden="true">*</span>
                  </h3>
                  <button
                    type="button"
                    className="reset-btn"
                    onClick={resetAiApiConfig}
                    title={theme.language === 'en' ? 'Reset' : '重置'}
                  >
                    <ArrowClockwise size={18} />
                    <span>{theme.language === 'en' ? 'Reset' : '重置'}</span>
                  </button>
                </div>
                <div
                  className={`grid-form ai-api-limits${aiModelPreset === AI_MODEL_CUSTOM ? ' has-custom' : ''}`}
                >
                  <div className="form-group">
                    <label>
                      {theme.language === 'en' ? 'Model' : '模型'}
                      <span className="required-dot" aria-hidden="true">*</span>
                    </label>
                    <div className="ai-model-dropdown" ref={aiModelDropdownRef}>
                      <button
                        type="button"
                        className="ai-model-dropdown-trigger"
                        aria-expanded={aiModelMenuOpen}
                        aria-haspopup="listbox"
                        onClick={() => setAiModelMenuOpen((open) => !open)}
                      >
                        <span className="ai-model-dropdown-value">
                          {theme.language === 'en' ? 'Google · gemini' : 'Google · gemini'}
                        </span>
                        <CaretDown
                          className={`ai-model-dropdown-chevron${aiModelMenuOpen ? ' is-open' : ''}`}
                          weight="bold"
                          size={18}
                          aria-hidden
                        />
                      </button>
                      {aiModelMenuOpen && (
                        <ul className="ai-model-dropdown-menu" role="listbox">
                          {AI_MODEL_OPTIONS.map((opt) => (
                            <li key={opt.value} role="none">
                              <button
                                type="button"
                                role="option"
                                aria-selected={aiModelPreset === opt.value}
                                className={`ai-model-dropdown-option${
                                  aiModelPreset === opt.value ? ' selected' : ''
                                }`}
                                onClick={() => {
                                  setAiModelPreset(opt.value);
                                  setAiModelMenuOpen(false);
                                }}
                              >
                                {theme.language === 'en' ? opt.labelEn : opt.labelZh}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                  {/* {aiModelPreset === AI_MODEL_CUSTOM && (
                    <div className="form-group full-width">
                      <label>{theme.language === 'en' ? 'Custom model id' : '自定义模型 ID'}</label>
                      <input
                        type="text"
                        className="form-input"
                        autoComplete="off"
                        placeholder={
                          theme.language === 'en' ? 'e.g. gpt-4.1 or vendor/model' : '例如 gpt-4.1 或 厂商/模型名'
                        }
                        value={aiCustomModel}
                        onChange={(e) => setAiCustomModel(e.target.value)}
                      />
                    </div>
                  )} */}
                  <div
                    className={`form-group${aiModelPreset === AI_MODEL_CUSTOM ? ' full-width' : ''}`}
                  >
                    <label>
                      {theme.language === 'en' ? 'API key' : 'API 密钥'}
                      <span className="required-dot" aria-hidden="true">*</span>
                    </label>
                    <input
                      type="password"
                      className="form-input"
                      autoComplete="off"
                      placeholder={
                        theme.language === 'en' ? 'Your LLM provider API key' : '填写大模型服务商提供的 API Key'
                      }
                      value={aiApiKey}
                      onChange={(e) => setAiApiKey(e.target.value)}
                    />
                  </div>
                </div>
                <p className="note-text">
                  {theme.language === 'en'
                    ? 'Note: Please use Tier1 or above API tiers. For countries or regions that cannot use Google services, you need to use VPN, otherwise the service may be unavailable.'
                    : '提示：API务必使用Tier1或以上等级的。对于无法使用Google服务的国家或地区需要使用VPN，否则会出现服务不可用的情况。'}
                </p>
              </section>

              <section className="form-section section-box">
                <div className="section-header">
                  <h3>{theme.language === 'en' ? 'Search Settings' : '检索参数设置'}</h3>
                  <button
                    className="reset-btn"
                    onClick={resetSearchSettings}
                    title={theme.language === 'en' ? 'Reset' : '重置'}
                  >
                    <ArrowClockwise size={18} />
                    <span>{theme.language === 'en' ? 'Reset' : '重置'}</span>
                  </button>
                </div>
                <div className="grid-form pubmed-limits">
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Max Rounds' : '最大迭代轮次'}</label>
                    <div className="number-input">
                      <input
                        type="text"
                        className="form-input"
                        value={maxRounds}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === '' || /^\d+$/.test(val)) {
                            setMaxRounds(val === '' ? '' : parseInt(val));
                          }
                        }}
                        onBlur={(e) => {
                          let val = parseInt(e.target.value);
                          if (isNaN(val) || val < 1) {
                            setMaxRounds(1);
                          } else if (val > 50) {
                            setMaxRounds(50);
                          } else {
                            setMaxRounds(val);
                          }
                        }}
                      />
                      <div className="spinners">
                        <CaretUp
                          weight="fill"
                          size={12}
                          onClick={() => handleMaxRoundsChange(1)}
                          style={{ cursor: 'pointer' }}
                        />
                        <CaretDown
                          weight="fill"
                          size={12}
                          onClick={() => handleMaxRoundsChange(-1)}
                          style={{ cursor: 'pointer' }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Auto Stop Articles' : '目标文献数量'}</label>
                    <div className="number-input">
                      <input
                        type="text"
                        className="form-input"
                        value={autoStopArticles}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === '' || /^\d+$/.test(val)) {
                            setAutoStopArticles(val === '' ? '' : parseInt(val));
                          }
                        }}
                        onBlur={(e) => {
                          let val = parseInt(e.target.value);
                          if (isNaN(val) || val < 1) {
                            setAutoStopArticles(1);
                          } else if (val > 500) {
                            setAutoStopArticles(500);
                          } else {
                            setAutoStopArticles(val);
                          }
                        }}
                      />
                      <div className="spinners">
                        <CaretUp
                          weight="fill"
                          size={12}
                          onClick={() => handleAutoStopArticlesChange(1)}
                          style={{ cursor: 'pointer' }}
                        />
                        <CaretDown
                          weight="fill"
                          size={12}
                          onClick={() => handleAutoStopArticlesChange(-1)}
                          style={{ cursor: 'pointer' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              {/* PubMed Search Limits */}
              <section className="form-section section-box">
                <div className="section-header">
                  <h3>{theme.language === 'en' ? 'PubMed Search Limits' : 'PubMed 检索限定条件'}</h3>
                  <button
                    className="reset-btn"
                    onClick={resetPubMedLimits}
                    title={theme.language === 'en' ? 'Reset' : '重置'}
                  >
                    <ArrowClockwise size={18} />
                    <span>{theme.language === 'en' ? 'Reset' : '重置'}</span>
                  </button>
                </div>
                <div className="grid-form pubmed-limits">
                  {/* Row 1 */}
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Time' : '发表时间'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. 2020:2025"
                      value={pubmedLimits.time}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, time: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Affiliation' : '作者单位'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g., Harvard"
                      value={pubmedLimits.affiliation}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, affiliation: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Journal' : '目标期刊'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g., NEJM"
                      value={pubmedLimits.journal}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, journal: e.target.value }))}
                    />
                  </div>

                  {/* Row 2 */}
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Author' : '作者姓名'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g., Author"
                      value={pubmedLimits.author}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, author: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'First Author' : '第一作者'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="First Author"
                      value={pubmedLimits.firstAuthor}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, firstAuthor: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>{theme.language === 'en' ? 'Last Author' : '通讯作者'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g., NEJM"
                      value={pubmedLimits.lastAuthor}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, lastAuthor: e.target.value }))}
                    />
                  </div>

                  {/* Row 3 */}
                  <div className="form-group full-width">
                    <label>{theme.language === 'en' ? 'Self Filter' : '自定义检索式'}</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder=""
                      value={pubmedLimits.selfFilter}
                      onChange={(e) => setPubmedLimits(prev => ({ ...prev, selfFilter: e.target.value }))}
                    />
                  </div>
                </div>
                <p className="note-text">{theme.language === 'en' ? 'Note: These limits match the PubMed search format and will be automatically added to the search query.' : '提示：以上限定条件将按照PubMed检索语法自动整合至检索式中。'}</p>
              </section>

              {/* Journal Limits */}
              <section className="form-section section-box">
                <div className="section-header">
                  <h3>{theme.language === 'en' ? 'Journal Limits' : '期刊筛选条件'}</h3>
                  <button
                    className="reset-btn"
                    onClick={resetJournalLimits}
                    title={theme.language === 'en' ? 'Reset' : '重置'}
                  >
                    <ArrowClockwise size={18} />
                    <span>{theme.language === 'en' ? 'Reset' : '重置'}</span>
                  </button>
                </div>
                <div className="limits-container">
                  {/* Impact Factor */}
                  <div className="limit-item" data-slider="if">
                    <label>{theme.language === 'en' ? 'Impact Factor (IF)' : '影响因子'}</label>
                    <div className="slider-row">
                      <div className="slider-value">{getImpactFactorDisplay()}</div>
                      <div className="range-slider" data-type="if">
                        <div className="range-track" style={getIfTrackStyle()}></div>
                        <input
                          ref={ifLeftRef}
                          type="range"
                          className="range-input left"
                          min="0"
                          max="100"
                          value={impactFactor.left}
                          onChange={(e) => updateImpactFactor(parseInt(e.target.value), true)}
                        />
                        <input
                          ref={ifRightRef}
                          type="range"
                          className="range-input right"
                          min="0"
                          max="100"
                          value={impactFactor.right}
                          onChange={(e) => updateImpactFactor(parseInt(e.target.value), false)}
                        />
                      </div>
                    </div>
                  </div>

                  {/* JCR Zone */}
                  <div className="limit-item" data-slider="jcr">
                    <label>{theme.language === 'en' ? 'Journal Citation Reports (JCR) Zone' : 'JCR分区'}</label>
                    <div className="slider-row">
                      <div className="slider-value">{getJcrZoneDisplay()}</div>
                      <div className="range-slider" data-type="jcr">
                        <div className="range-track" style={getJcrTrackStyle()}></div>
                        <input
                          ref={jcrLeftRef}
                          type="range"
                          className="range-input left"
                          min="1"
                          max="4"
                          value={jcrZone.left}
                          onChange={(e) => updateJcrZone(parseInt(e.target.value), true)}
                        />
                        <input
                          ref={jcrRightRef}
                          type="range"
                          className="range-input right"
                          min="1"
                          max="4"
                          value={jcrZone.right}
                          onChange={(e) => updateJcrZone(parseInt(e.target.value), false)}
                        />
                      </div>
                    </div>
                  </div>

                  {/* CAS Zone */}
                  <div className="limit-item" data-slider="cas">
                    <label>{theme.language === 'en' ? 'Chinese Academy of Sciences(CAS) Zone' : '中科院分区'}</label>
                    <div className="slider-row">
                      <div className="slider-value">{getCasZoneDisplay()}</div>
                      <div className="range-slider" data-type="cas">
                        <div className="range-track" style={getCasTrackStyle()}></div>
                        <input
                          ref={casLeftRef}
                          type="range"
                          className="range-input left"
                          min="1"
                          max="4"
                          value={casZone.left}
                          onChange={(e) => updateCasZone(parseInt(e.target.value), true)}
                        />
                        <input
                          ref={casRightRef}
                          type="range"
                          className="range-input right"
                          min="1"
                          max="4"
                          value={casZone.right}
                          onChange={(e) => updateCasZone(parseInt(e.target.value), false)}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </section>
              {/* Output Language */}
              <section className="form-section section-box">
                <div className="section-header">
                  <h3>{theme.language === 'en' ? 'Output Language' : '输出语言'}</h3>
                </div>
                <div className="language-options">
                  {OUTPUT_LANGUAGES.map((lang) => (
                    <label key={lang.value} className="lang-option">
                      <input
                        type="radio"
                        name="language"
                        value={lang.value}
                        checked={outputLanguage === lang.value}
                        onChange={(e) => setOutputLanguage(e.target.value)}
                      />
                      <span className="lang-pill">
                        <img src={lang.flag} alt={lang.name.en} />
                        <span className="lang-name">{lang.name[theme.language] || lang.name.en}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </section>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div >
  );
};

