import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@/utils/ThemeContext';
import { Cookies } from '@/utils/cookies';
import { DownloadSimple, Stop, ArrowClockwise, FileText, CheckCircle, Files, ArrowsOut, ArrowsIn } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'framer-motion';
import { TaskStatus, getStatusText } from '@/utils/taskStatus';
import { ConfirmModal } from '@/components/PopUpWindows/ConfirmWindow';
import { useToast } from '@/components/Toast/ToastContext';
import { getSearchStatus, downloadSearchResult, stopSearchTask } from '@/api/Search/searchApi';
import { RetrievalItem, SearchProgress, ArticleData } from '@/interface/search/searchInterface';
import { BackButton } from '@/components/BackButton/BackButton';
import '@/styles/taskStatus.css';
import './SearchResult.css';

interface LiteratureSearchResultProps {
  status?: TaskStatus;
}

const columnName =
{
  "zh": {
    "序号": "序号",
    "匹配度评分": "匹配度评分",
    "期刊名称": "期刊名称",
    "ISSN": "ISSN",
    "中科院分区": "中科院分区",
    "JCR分区": "JCR分区",
    "最新IF": "最新IF",
    "5年IF": "5年IF",
    "排名": "排名",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "文章标题",
    "第一作者": "第一作者",
    "通讯作者": "通讯作者",
    "第一作者单位": "第一作者单位",
    "发表时间": "发表时间",
    "研究目的": "研究目的",
    "研究类型": "研究类型",
    "研究方法": "研究方法",
    "研究对象": "研究对象",
    "主要研究结果": "主要研究结果",
    "研究结论与意义": "研究结论与意义",
    "研究亮点或创新点": "研究亮点或创新点",
    "PubMed链接": "PubMed Link",
    "PMC链接": "全文链接"
  },
  "en": {
    "序号": "No.",
    "匹配度评分": "Relevance Score",
    "期刊名称": "Journal Name",
    "ISSN": "ISSN",
    "中科院分区": "CAS Partition",
    "JCR分区": "JCR Partition",
    "最新IF": "Latest IF",
    "5年IF": "5-Year IF",
    "排名": "Ranking",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Article Title",
    "第一作者": "First Author",
    "通讯作者": "Corresponding Author",
    "第一作者单位": "First Author Affiliation",
    "发表时间": "Publication Date",
    "研究目的": "Research Objective",
    "研究类型": "Study Type",
    "研究方法": "Research Method",
    "研究对象": "Study Population",
    "主要研究结果": "Main Results",
    "研究结论与意义": "Conclusions and Significance",
    "研究亮点或创新点": "Highlights and Innovations",
    "PubMed链接": "PubMed Link",
    "PMC链接": "Full Text Link"
  },
  "es": {
    "序号": "Núm.",
    "匹配度评分": "Puntuación de Relevancia",
    "期刊名称": "Nombre de la Revista",
    "ISSN": "ISSN",
    "中科院分区": "Partición CAS",
    "JCR分区": "Partición JCR",
    "最新IF": "IF Más Reciente",
    "5年IF": "IF de 5 Años",
    "排名": "Clasificación",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Título del Artículo",
    "第一作者": "Primer Autor",
    "通讯作者": "Autor Correspondiente",
    "第一作者单位": "Afiliación del Primer Autor",
    "发表时间": "Fecha de Publicación",
    "研究目的": "Objetivo de Investigación",
    "研究类型": "Tipo de Estudio",
    "研究方法": "Método de Investigación",
    "研究对象": "Población de Estudio",
    "主要研究结果": "Resultados Principales",
    "研究结论与意义": "Conclusiones y Significado",
    "研究亮点或创新点": "Aspectos Destacados e Innovaciones",
    "PubMed链接": "Enlace PubMed",
    "PMC链接": "Enlace Full Text"
  },
  "fr": {
    "序号": "N°",
    "匹配度评分": "Score de Pertinence",
    "期刊名称": "Nom de la Revue",
    "ISSN": "ISSN",
    "中科院分区": "Partition CAS",
    "JCR分区": "Partition JCR",
    "最新IF": "IF le Plus Récent",
    "5年IF": "IF sur 5 Ans",
    "排名": "Classement",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Titre de l'Article",
    "第一作者": "Premier Auteur",
    "通讯作者": "Auteur Correspondant",
    "第一作者单位": "Affiliation du Premier Auteur",
    "发表时间": "Date de Publication",
    "研究目的": "Objectif de Recherche",
    "研究类型": "Type d'Étude",
    "研究方法": "Méthode de Recherche",
    "研究对象": "Population d'Étude",
    "主要研究结果": "Résultats Principaux",
    "研究结论与意义": "Conclusions et Signification",
    "研究亮点或创新点": "Points Forts et Innovations",
    "PubMed链接": "Lien PubMed",
    "PMC链接": "Lien Full Text"
  },
  "pt": {
    "序号": "Nº",
    "匹配度评分": "Pontuação de Relevância",
    "期刊名称": "Nome da Revista",
    "ISSN": "ISSN",
    "中科院分区": "Partição CAS",
    "JCR分区": "Partição JCR",
    "最新IF": "IF Mais Recente",
    "5年IF": "IF de 5 Anos",
    "排名": "Classificação",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Título do Artigo",
    "第一作者": "Primeiro Autor",
    "通讯作者": "Autor Correspondente",
    "第一作者单位": "Afiliação do Primeiro Autor",
    "发表时间": "Data de Publicação",
    "研究目的": "Objetivo da Pesquisa",
    "研究类型": "Tipo de Estudo",
    "研究方法": "Método de Pesquisa",
    "研究对象": "População do Estudo",
    "主要研究结果": "Resultados Principais",
    "研究结论与意义": "Conclusões e Significado",
    "研究亮点或创新点": "Destaques e Inovações",
    "PubMed链接": "Link PubMed",
    "PMC链接": "Link Full Text"
  },
  "it": {
    "序号": "N.",
    "匹配度评分": "Punteggio di Rilevanza",
    "期刊名称": "Nome della Rivista",
    "ISSN": "ISSN",
    "中科院分区": "Partizione CAS",
    "JCR分区": "Partizione JCR",
    "最新IF": "IF Più Recente",
    "5年IF": "IF a 5 Anni",
    "排名": "Classifica",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Titolo dell'Articolo",
    "第一作者": "Primo Autore",
    "通讯作者": "Autore Corrispondente",
    "第一作者单位": "Affiliazione del Primo Autore",
    "发表时间": "Data di Pubblicazione",
    "研究目的": "Obiettivo della Ricerca",
    "研究类型": "Tipo di Studio",
    "研究方法": "Metodo di Ricerca",
    "研究对象": "Popolazione dello Studio",
    "主要研究结果": "Risultati Principali",
    "研究结论与意义": "Conclusioni e Significato",
    "研究亮点或创新点": "Punti Salienti e Innovazioni",
    "PubMed链接": "Link PubMed",
    "PMC链接": "Link Full Text"
  },
  "de": {
    "序号": "Nr.",
    "匹配度评分": "Relevanzbewertung",
    "期刊名称": "Zeitschriftenname",
    "ISSN": "ISSN",
    "中科院分区": "Kategorieaufteilung",
    "JCR分区": "JCR-Aufteilung",
    "最新IF": "Neuester IF",
    "5年IF": "5-Jahres-IF",
    "排名": "Rangfolge",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Artikeltitel",
    "第一作者": "Erstautor",
    "通讯作者": "Korrespondierender Autor",
    "第一作者单位": "Zugehörigkeit des Erstautors",
    "发表时间": "Veröffentlichungsdatum",
    "研究目的": "Forschungsziel",
    "研究类型": "Studientyp",
    "研究方法": "Forschungsmethode",
    "研究对象": "Studienpopulation",
    "主要研究结果": "Hauptergebnisse",
    "研究结论与意义": "Schlussfolgerungen und Bedeutung",
    "研究亮点或创新点": "Highlights und Innovationen",
    "PubMed链接": "PubMed-Link",
    "PMC链接": "Full Text Link"
  },
  "ru": {
    "序号": "№",
    "匹配度评分": "Оценка Релевантности",
    "期刊名称": "Название Журнала",
    "ISSN": "ISSN",
    "中科院分区": "Категория Раздела",
    "JCR分区": "Раздел JCR",
    "最新IF": "Последний IF",
    "5年IF": "5-летний IF",
    "排名": "Рейтинг",
    "PMID": "PMID",
    "PMCID": "PMCID",
    "文章标题": "Название Статьи",
    "第一作者": "Первый Автор",
    "通讯作者": "Корреспондирующий Автор",
    "第一作者单位": "Принадлежность Первого Автора",
    "发表时间": "Дата Публикации",
    "研究目的": "Цель Исследования",
    "研究类型": "Тип Исследования",
    "研究方法": "Метод Исследования",
    "研究对象": "Популяция Исследования",
    "主要研究结果": "Основные Результаты",
    "研究结论与意义": "Выводы и Значение",
    "研究亮点或创新点": "Основные Моменты и Инновации",
    "PubMed链接": "Ссылка PubMed",
    "PMC链接": "Ссылка Full Text"
  }
}


// 定义表格列的顺序（使用中文 key）
const tableColumnOrder = [
  "序号",
  "期刊名称",
  "文章标题",
  "发表时间",
  "研究目的",
  "研究类型",
  "研究方法",
  "研究对象",
  "主要研究结果",
  "研究结论与意义",
  "研究亮点或创新点",
  "第一作者",
  "通讯作者",
  "第一作者单位",
  "ISSN",
  "中科院分区",
  "JCR分区",
  "最新IF",
  "5年IF",
  "排名",
  "PMID",
  "PubMed链接",
  "PMC链接"
];

// 获取当前语言的列名
const getColumnName = (columnKey: string, language: string): string => {
  const lang = language as keyof typeof columnName;
  if (columnName[lang] && columnName[lang][columnKey as keyof typeof columnName[typeof lang]]) {
    return columnName[lang][columnKey as keyof typeof columnName[typeof lang]];
  }
  // 如果找不到翻译，返回中文
  return columnName.zh[columnKey as keyof typeof columnName.zh] || columnKey;
};

type RelevanceLevel = 'high' | 'moderate' | 'low';

// 需要计算宽度的列（排除序号、日期等短字段）
// const columnsToCalculate: (keyof TableRowData)[] = ['journal', 'objective', 'type', 'method', 'population', 'outcome']; // Removed

export const LiteratureSearchResult: React.FC<LiteratureSearchResultProps> = ({ status: initialStatus = 'Running' }) => {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [showContent, setShowContent] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [relevanceLevel, setRelevanceLevel] = useState<RelevanceLevel>('high');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // State for dynamic data
  const [status, setStatus] = useState<TaskStatus>(initialStatus);
  const [retrievalList, setRetrievalList] = useState<RetrievalItem[]>([]);
  const [searchProgress, setSearchProgress] = useState<SearchProgress>({
    current_round: 0,
    current_round_retrieved_articles: 0,
    total_selected_articles: 0,
    total_retrieved_articles: 0,
    max_round: 0,
    auto_stop_articles: 0
  });
  const [outputReview, setOutputReview] = useState<ArticleData[]>([]);
  const [downloadLink, setDownloadLink] = useState<string>('');

  // 从 cookies 获取 outputLanguage，默认英文
  const outputLanguage = Cookies.getOutputLanguage() || 'en';

  useEffect(() => {
    const taskIdObj = Cookies.getSearchTaskId();
    if (!taskIdObj?.taskId) return;
    const taskId = taskIdObj.taskId;

    const pollStatus = async () => {
      // Assuming /api/search proxies to search server
      if (!taskId) return;

      const res = await getSearchStatus(taskId);

      if (res.success && res.data) {
        setStatus(res.data.search_status as TaskStatus);
        const rawList = res.data.retrieval || [];
        const uniqueList = rawList.filter((item) => item.retrieval_title && item.retrieval_content)
          .filter((item, index, self) =>
            index === self.findIndex((t) => t.retrieval_title === item.retrieval_title)
          );
        setRetrievalList(uniqueList);
        setSearchProgress(res.data.search_progress || {
          current_round: 0,
          current_round_retrieved_articles: 0,
          total_selected_articles: 0,
          total_retrieved_articles: 0,
          max_round: 0,
          auto_stop_articles: 0
        });
        setOutputReview(res.data.output_review || []);
        if (res.data.download_link) {
          setDownloadLink(res.data.download_link);
        }
      }
    };

    const intervalId = setInterval(pollStatus, 2000);
    pollStatus(); // Initial call

    return () => clearInterval(intervalId);
  }, []);

  // 默认延迟显示内容，等待 search status 过渡动画完成
  useEffect(() => {
    // 作为后备方案，如果 onAnimationComplete 没有触发
    const timer = setTimeout(() => {
      setShowContent(true);
    }, 200);
    return () => clearTimeout(timer);
  }, []);

  const handleStopClick = () => {
    setShowStopConfirm(true);
  };

  const handleConfirmStop = async () => {
    const taskIdObj = Cookies.getSearchTaskId();
    if (taskIdObj?.taskId) {
      const res = await stopSearchTask(taskIdObj.taskId);
      if (res.success) {
        showToast(
          theme.language === 'en' ? 'Task stopped successfully' : '任务已停止',
          'success'
        );
        Cookies.removeSearchTaskId();
        navigate('/search');
      } else {
        showToast(
          theme.language === 'en' ? 'Failed to stop task' : '停止任务失败',
          'error'
        );
      }
    }
    setShowStopConfirm(false);
  };

  const handleCancelStop = () => {
    setShowStopConfirm(false);
  };

  // Page-level fullscreen functionality (not browser fullscreen)
  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // Helper to map Chinese column names to ArticleData keys
  const getArticleDataKey = (chineseColumnName: string): keyof ArticleData | null => {
    switch (chineseColumnName) {
      case "序号": return "no.";
      case "匹配度评分": return "score";
      case "期刊名称": return "journal_name";
      case "文章标题": return "article_title";
      case "发表时间": return "publication_date";
      case "研究目的": return "research_objective";
      case "研究类型": return "study_type";
      case "研究方法": return "research_method";
      case "研究对象": return "study_population";
      case "主要研究结果": return "main_results";
      case "研究结论与意义": return "conclusions_and_significance";
      case "研究亮点或创新点": return "highlights_and_innovations";
      case "第一作者": return "first_author";
      case "通讯作者": return "corresponding_author";
      case "第一作者单位": return "first_author_affiliation";
      case "ISSN": return "issn";
      case "中科院分区": return "category_partition";
      // "大类分区" is not directly in ArticleData, handled below
      case "JCR分区": return "jcr_partition";
      case "最新IF": return "latest_if";
      case "5年IF": return "5-year_if";
      case "排名": return "ranking";
      case "PMID": return "pmid";
      case "PubMed链接": return "pubmed_link";
      case "PMC链接": return "pmc_link";
      default: return null;
    }
  };

  // Calculate real-time statistics
  const stats = React.useMemo(() => {
    // 1. Relevance
    let relHigh = 0, relMod = 0, relLow = 0;
    // 2. IF
    let ifHigh = 0, ifMod = 0, ifLow = 0, ifLowest = 0;
    // 3. JCR
    let q1 = 0, q2 = 0, q3 = 0, q4 = 0;
    // 4. Journals
    const journalCounts: Record<string, number> = {};

    outputReview.forEach(row => {
      // Relevance
      const s = String(row.score || '');
      if (s.includes('3')) relHigh++;
      else if (s.includes('2')) relMod++;
      else if (s.includes('1')) relLow++;
      // Treat unknown as low or ignore? Treating as Low to sum up to total
      else relLow++;

      // IF
      const ifText = String(row.latest_if || '');
      // Extract number: "3.5" -> 3.5, "N/A" -> 0
      const ifVal = parseFloat(ifText.replace(/[^0-9.]/g, ''));
      const safeIf = isNaN(ifVal) ? 0 : ifVal;

      if (safeIf >= 10) ifHigh++;
      else if (safeIf >= 5) ifMod++;
      else if (safeIf >= 3) ifLow++;
      else ifLowest++;

      // JCR
      const jcr = String(row.jcr_partition || '').toUpperCase();
      if (jcr.includes('1') || jcr.includes('Q1')) q1++;
      else if (jcr.includes('2') || jcr.includes('Q2')) q2++;
      else if (jcr.includes('3') || jcr.includes('Q3')) q3++;
      else if (jcr.includes('4') || jcr.includes('Q4')) q4++;

      // Journal
      const jName = row.journal_name;
      if (jName && jName !== 'N/A') {
        journalCounts[jName] = (journalCounts[jName] || 0) + 1;
      }
    });

    const realTotal = outputReview.length;

    // Top Journals (Sort by count desc, take top 5)
    const sortedJournals = Object.entries(journalCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([name, count], idx) => ({ rank: idx + 1, name, count }));

    return {
      rel: { high: relHigh, mod: relMod, low: relLow, total: realTotal },
      ifDist: { high: ifHigh, mod: ifMod, low: ifLow, lowest: ifLowest },
      jcr: { q1, q2, q3, q4, total: realTotal }, // Note: JCR total might strictly be q1+q2+q3+q4 if some missing
      journals: sortedJournals
    };
  }, [outputReview]);

  // Helper for percentages
  const getPct = (val: number, total: number) => total > 0 ? ((val / total) * 100) : 0;
  const getPctStr = (val: number, total: number) => `${getPct(val, total).toFixed(1)}%`;

  const leaveResult = () => {
    navigate('/search/task');
    const temptaskId = Cookies.getSearchTaskId()?.taskId;
    if (temptaskId) {
      Cookies.setSearchTaskId({ taskId: temptaskId, display: false });
    }
  };

  return (
    <div className="result-page-container">
      {/* Fixed Status Area */}
      <div className="fixed-status-area">
        <BackButton onClick={leaveResult} />
        <motion.section
          layoutId="search-input-container"
          layout={false}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 30,
          }}
          onAnimationComplete={() => {
            // 动画完成后显示下方内容
            setShowContent(true);
          }}
          className={`status-section section-box ${status}`}
        >
          <div className="section-header-row">
            <h2 className="section-title-with-dot">
              <span className={`status-dot-indicator ${status}`}></span>
              <span>{theme.language === 'en' ? 'Search Status' : '检索状态'}</span>
            </h2>
            <div className={`status-badge ${status}`}>{getStatusText(status || 'Waiting', theme.language)}</div>
            {status !== 'Success' && status !== 'Failed' && (
              <button
                className="stop-btn"
                title={theme.language === 'en' ? 'Stop' : '停止'}
                onClick={handleStopClick}
              >
                <Stop size={18} weight="fill" />
                <span>{theme.language === 'en' ? 'Stop it' : '停止'}</span>
              </button>
            )}
            {(status === 'Success' || status === 'Failed') && (
              <button
                className="download-btn"
                title={theme.language === 'en' ? 'Download Excel' : '下载 Excel'}
                onClick={() => {
                  if (downloadLink) {
                    downloadSearchResult(downloadLink);
                    // Clear task ID cookie after download starts
                    Cookies.removeSearchTaskId();
                    navigate('/search');
                  }
                }}
                disabled={!downloadLink}
                style={{ opacity: !downloadLink ? 0.5 : 1, cursor: !downloadLink ? 'not-allowed' : 'pointer' }}
              >
                <DownloadSimple size={18} weight="bold" />
                <span>{theme.language === 'en' ? 'Download' : '下载'}</span>
              </button>
            )}
          </div>
        </motion.section>
      </div>

      {/* Scrollable Content Area */}
      <AnimatePresence>
        {showContent && (
          <motion.div
            className="result-content-scroll"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Retrieval Panel */}
            <div className="status-panels">
              <div className="retrieval-panel">
                <h3 className="panel-title">
                  <span className="status-dot-indicator active"></span>
                  <span>{theme.language === 'en' ? 'Retrieval' : '检索'}</span>
                </h3>
                <div className="retrieval-content">
                  {retrievalList.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="retrieval-item"
                    >
                      <div className="retrieval-title">{item.retrieval_title}</div>
                      <div className="query-text">{item.retrieval_content}</div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Search Progress Panel */}
              <div className="progress-panel">
                <h3 className="panel-title">
                  <span className="status-dot-indicator active"></span>
                  <span>{theme.language === 'en' ? 'Search Progress' : '检索进度'}</span>
                </h3>
                <div className="progress-grid">
                  <div className="progress-card">
                    <div className="progress-label">
                      <ArrowClockwise
                        size={28}
                        weight="regular"
                        className={`progress-icon ${status === 'Running' ? 'icon-rotate' : ''}`}
                      />
                      <span>{theme.language === 'en' ? 'Current Round' : '当前轮次'}</span>
                    </div>
                    <div className="progress-value">{searchProgress.current_round} / {searchProgress.max_round}</div>
                  </div>
                  <div className="progress-card">
                    <div className="progress-label">
                      <FileText
                        size={28}
                        weight="regular"
                        className={`progress-icon ${status === 'Running' ? 'icon-pulse' : ''}`}
                      />
                      <span>{theme.language === 'en' ? 'Current Round Retrieved Articles' : '当前轮次检索文献'}</span>
                    </div>
                    <div className="progress-value">{searchProgress.current_round_retrieved_articles}</div>
                  </div>
                  <div className="progress-card">
                    <div className="progress-label">
                      <CheckCircle
                        size={28}
                        weight="regular"
                        className={`progress-icon ${status === 'Running' ? 'icon-pulse' : ''}`}
                      />
                      <span>{theme.language === 'en' ? 'Total Selected Articles' : '总纳入文献'}</span>
                    </div>
                    <div className="progress-value">{searchProgress.total_selected_articles}/{searchProgress.auto_stop_articles}</div>
                  </div>
                  <div className="progress-card">
                    <div className="progress-label">
                      <Files
                        size={28}
                        weight="regular"
                        className={`progress-icon ${status === 'Running' ? 'icon-pulse' : ''}`}
                      />
                      <span>{theme.language === 'en' ? 'Total Retrieved Articles' : '总检索文献'}</span>
                    </div>
                    <div className="progress-value">{searchProgress.total_retrieved_articles}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Output Review Section */}
            <motion.section
              className={`output-section section-box ${isFullscreen ? 'fullscreen-mode' : ''}`}
              layout
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
              }}
            >
              <motion.div
                className="section-header-row"
                layout
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 30,
                }}
              >
                <h2 className="section-title-with-dot">
                  <span className="status-dot-indicator active"></span>
                  <span>{theme.language === 'en' ? 'Output Review' : '输出结果'}</span>
                </h2>
                <div className="relevance-buttons">
                  {['high', 'moderate', 'low'].map(level => (
                    <motion.button
                      key={level}
                      className={`relevance-btn ${relevanceLevel === level ? 'active' : ''}`}
                      onClick={() => setRelevanceLevel(level as RelevanceLevel)}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ type: "spring", stiffness: 400, damping: 17 }}
                    >
                      {level === 'high' ? (theme.language === 'en' ? 'Highly Relevant' : '高度相关') :
                        level === 'moderate' ? (theme.language === 'en' ? 'Moderately Relevant' : '中度相关') :
                          (theme.language === 'en' ? 'Low Relevant' : '低度相关')}
                    </motion.button>
                  ))}
                </div>

                <motion.button
                  className="fullscreen-btn"
                  onClick={handleFullscreen}
                  title={theme.language === 'en' ? (isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen') : (isFullscreen ? '退出全屏' : '进入全屏')}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  transition={{ type: "spring", stiffness: 400, damping: 17 }}
                >
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={isFullscreen ? 'in' : 'out'}
                      initial={{ opacity: 0, rotate: -90, scale: 0.8 }}
                      animate={{ opacity: 1, rotate: 0, scale: 1 }}
                      exit={{ opacity: 0, rotate: 90, scale: 0.8 }}
                      transition={{
                        duration: 0.25,
                        ease: [0.4, 0, 0.2, 1]
                      }}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    >
                      {isFullscreen ? <ArrowsIn size={18} weight="bold" /> : <ArrowsOut size={18} weight="bold" />}
                    </motion.div>
                  </AnimatePresence>
                </motion.button>
              </motion.div>

              <motion.div
                className={`table-wrapper ${isFullscreen ? 'fullscreen-table' : ''}`}
                layout
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 30,
                }}
              >
                <div className="table-container">
                  <table className="result-table">
                    <thead>
                      <tr>
                        {tableColumnOrder.map((columnKey) => (
                          <th
                            key={columnKey}
                            className={`col-${columnKey.replace(/\s+/g, '-').toLowerCase()}`}
                          >
                            {getColumnName(columnKey, outputLanguage)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {outputReview.filter((row) => {
                        const scoreStr = String(row.score || '');
                        if (relevanceLevel === 'high') return scoreStr.includes('3');
                        if (relevanceLevel === 'moderate') return scoreStr.includes('2');
                        if (relevanceLevel === 'low') return scoreStr.includes('1');
                        return true;
                      }).map((row, index) => (
                        <tr key={row["no."]}>
                          {tableColumnOrder.map((columnKey) => {
                            const dataKey = getArticleDataKey(columnKey);
                            let content: React.ReactNode = '';

                            if (dataKey) {
                              if (dataKey === "no.") {
                                // Re-calculate sequence number based on current filtered view
                                content = index + 1;
                              } else if (dataKey === "pubmed_link" || dataKey === "pmc_link") {
                                const link = row[dataKey];
                                if (link) {
                                  content = <a href={link} target="_blank" rel="noopener noreferrer">{columnKey === "PubMed链接" ? "PubMed" : "PMC"}</a>;
                                }
                              } else {
                                content = String(row[dataKey] || '');
                              }
                            } else if (columnKey === "大类分区") {
                              // "大类分区" is not directly in ArticleData, display N/A or empty
                              content = "N/A";
                            }

                            return (
                              <td key={columnKey}>
                                <div className="cell-content">{content}</div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {outputReview.length === 0 && <div style={{ padding: '2rem', textAlign: 'center', color: '#888' }}>Waiting for results...</div>}
                </div>
              </motion.div>
            </motion.section>

            {/* Statistics Section */}
            <section className="statistics-section section-box">
              <h2 className="section-title-with-dot">
                <span className="status-dot-indicator active"></span>
                <span>{theme.language === 'en' ? 'Literature Statistics' : '文献统计'}</span>
              </h2>

              <div className="stats-grid">
                {/* Relevance Distribution */}
                <div className="stat-card">
                  <h3 className="stat-card-title">{theme.language === 'en' ? 'Relevance Distribution' : '相关性分布'}</h3>
                  <div className="stat-chart" id="relevanceChart">
                    <div className="bar-chart">
                      <div className="bar-item">
                        <span className="bar-label">{theme.language === 'en' ? 'High' : '高'}</span>
                        <div className="bar-track">
                          <div className="bar-fill high" style={{ width: getPctStr(stats.rel.high, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.rel.high}</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">{theme.language === 'en' ? 'Medium' : '中'}</span>
                        <div className="bar-track">
                          <div className="bar-fill medium" style={{ width: getPctStr(stats.rel.mod, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.rel.mod}</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">{theme.language === 'en' ? 'Low' : '低'}</span>
                        <div className="bar-track">
                          <div className="bar-fill low" style={{ width: getPctStr(stats.rel.low, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.rel.low}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Impact Factor Distribution */}
                <div className="stat-card">
                  <h3 className="stat-card-title">{theme.language === 'en' ? 'Impact Factor Distribution' : '影响因子分布'}</h3>
                  <div className="stat-chart" id="ifChart">
                    <div className="bar-chart">
                      <div className="bar-item">
                        <span className="bar-label">IF ≥ 10</span>
                        <div className="bar-track">
                          <div className="bar-fill if-high" style={{ width: getPctStr(stats.ifDist.high, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.ifDist.high}</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">5 ≤ IF &lt; 10</span>
                        <div className="bar-track">
                          <div className="bar-fill if-medium" style={{ width: getPctStr(stats.ifDist.mod, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.ifDist.mod}</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">3 ≤ IF &lt; 5</span>
                        <div className="bar-track">
                          <div className="bar-fill if-low" style={{ width: getPctStr(stats.ifDist.low, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.ifDist.low}</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">IF &lt; 3</span>
                        <div className="bar-track">
                          <div className="bar-fill if-lowest" style={{ width: getPctStr(stats.ifDist.lowest, stats.rel.total) }}></div>
                        </div>
                        <span className="bar-value">{stats.ifDist.lowest}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* JCR Zone Distribution */}
                <div className="stat-card">
                  <h3 className="stat-card-title">{theme.language === 'en' ? 'JCR Zone Distribution' : 'JCR 分区分布'}</h3>
                  <div className="stat-chart jcr-chart-container" id="jcrChart">
                    <div className="pie-chart-wrapper">
                      <svg className="pie-chart" viewBox="0 0 120 120">
                        {(() => {
                          // Dynamic Pie Chart Calculation
                          const r = 45;
                          const C = 2 * Math.PI * r; // ~282.74
                          const total = stats.jcr.total || 1;

                          const q1Len = (stats.jcr.q1 / total) * C;
                          const q2Len = (stats.jcr.q2 / total) * C;
                          const q3Len = (stats.jcr.q3 / total) * C;
                          const q4Len = (stats.jcr.q4 / total) * C;

                          // Offsets (accumulated length, negative direction)
                          const q1Off = 0; // Starts at 0 (top/right depending on rotation)
                          const q2Off = -q1Len;
                          const q3Off = -(q1Len + q2Len);
                          const q4Off = -(q1Len + q2Len + q3Len);

                          return (
                            <>
                              {stats.jcr.q1 > 0 && <circle className="pie-segment q1" cx="60" cy="60" r="45" strokeDasharray={`${q1Len} ${C}`} strokeDashoffset={q1Off} />}
                              {stats.jcr.q2 > 0 && <circle className="pie-segment q2" cx="60" cy="60" r="45" strokeDasharray={`${q2Len} ${C}`} strokeDashoffset={q2Off} />}
                              {stats.jcr.q3 > 0 && <circle className="pie-segment q3" cx="60" cy="60" r="45" strokeDasharray={`${q3Len} ${C}`} strokeDashoffset={q3Off} />}
                              {stats.jcr.q4 > 0 && <circle className="pie-segment q4" cx="60" cy="60" r="45" strokeDasharray={`${q4Len} ${C}`} strokeDashoffset={q4Off} />}
                            </>
                          );
                        })()}
                      </svg>
                      <div className="pie-center">
                        <span className="pie-total">{stats.jcr.total}</span>
                        <span className="pie-label">{theme.language === 'en' ? 'Total' : '总计'}</span>
                      </div>
                    </div>
                    <div className="pie-legend">
                      <div className="legend-item">
                        <span className="legend-color q1"></span>
                        <span className="legend-label">Q1</span>
                        <span className="legend-value">{stats.jcr.q1} ({getPctStr(stats.jcr.q1, stats.jcr.total)})</span>
                      </div>
                      <div className="legend-item">
                        <span className="legend-color q2"></span>
                        <span className="legend-label">Q2</span>
                        <span className="legend-value">{stats.jcr.q2} ({getPctStr(stats.jcr.q2, stats.jcr.total)})</span>
                      </div>
                      <div className="legend-item">
                        <span className="legend-color q3"></span>
                        <span className="legend-label">Q3</span>
                        <span className="legend-value">{stats.jcr.q3} ({getPctStr(stats.jcr.q3, stats.jcr.total)})</span>
                      </div>
                      <div className="legend-item">
                        <span className="legend-color q4"></span>
                        <span className="legend-label">Q4</span>
                        <span className="legend-value">{stats.jcr.q4} ({getPctStr(stats.jcr.q4, stats.jcr.total)})</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Top Journals */}
                <div className="stat-card">
                  <h3 className="stat-card-title">{theme.language === 'en' ? 'Top Journals' : '顶级期刊'}</h3>
                  <div className="stat-chart" id="journalChart">
                    <div className="journal-list">
                      {stats.journals.map((j) => (
                        <div className="journal-item" key={j.name}>
                          <span className="journal-rank">{j.rank}</span>
                          <span className="journal-name" title={j.name}>{j.name}</span>
                          <span className="journal-count">{j.count}</span>
                        </div>
                      ))}
                      {stats.journals.length === 0 && <div style={{ textAlign: 'center', color: '#999', padding: '1rem' }}>No journal data</div>}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stop Confirmation Modal */}
      <ConfirmModal
        isOpen={showStopConfirm}
        onClose={handleCancelStop}
        onConfirm={handleConfirmStop}
        title={theme.language === 'en' ? 'Confirm Stop Task' : '确认停止任务'}
        message={theme.language === 'en'
          ? 'Are you sure you want to stop this task? This action cannot be undone.'
          : '您确定要停止此任务吗？此操作不可逆。'}
        confirmText={theme.language === 'en' ? 'Confirm' : '确认'}
        cancelText={theme.language === 'en' ? 'Cancel' : '取消'}
        confirmButtonColor="red"
      />
    </div >
  );
};