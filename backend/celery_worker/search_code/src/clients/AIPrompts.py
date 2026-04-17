import logging
from abc import ABC, abstractmethod
from typing import List
import threading
import random

# Configure the logger for this module
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. 通用的 API 密钥管理器
# ==============================================================================
class APIKeyManager:
    """
    管理多个API密钥，支持在遇到配额耗尽等问题时自动切换。
    线程安全，支持并发环境。
    """
    def __init__(self, api_keys: List[str]):
        if not api_keys or len(api_keys) == 0:
            raise ValueError("At least one API key must be provided")

        self.api_keys = api_keys
        self.lock = threading.Lock()

        if len(api_keys) > 1:
            self.current_index = random.randint(0, len(api_keys) - 1)
            logger.info(f"🔑 API Key Manager initialized successfully with {len(api_keys)} keys. Starting with key #{self.current_index + 1}")
        else:
            self.current_index = 0
            logger.info(f"🔑 API Key Manager initialized successfully with {len(api_keys)} key(s).")

    def get_current_key(self) -> str:
        """获取当前使用的API密钥"""
        with self.lock:
            return self.api_keys[self.current_index]

    def get_current_index(self) -> int:
        """获取当前API密钥的索引"""
        with self.lock:
            return self.current_index

    def switch_to_next_key(self) -> tuple[str, int]:
        """切换到下一个API密钥（循环）"""
        with self.lock:
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            new_key = self.api_keys[self.current_index]
            logger.warning(f"🔄 Switching API key: #{old_index + 1} → #{self.current_index + 1} (out of {len(self.api_keys)} keys)")
            return new_key, self.current_index

# ==============================================================================
# 2. 集中管理的提示词
# ==============================================================================
class ClientPrompts:
    """
    一个静态类，用于存储和格式化所有共享的提示词。
    """
    @staticmethod
    def get_generate_pubmed_query_prompt(user_query: str, attempt_number: int = 1) -> str:
        return f"""
        **避免在开头出现"```pubmed"诸如此类的废话！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！直接给我我可以直接复制到pubmed检索框上进行检索的检索式就好而无需其他任何废话！！**

        **第{attempt_number}轮检索 - 基于用户问题"{user_query}"生成检索式**

        **重要：请按以下三步分析法生成检索式**

        ---

        **第一步：核心概念提取 (Core Concept Extraction)**

        将用户查询 `"{user_query}"` 拆解为2-5个最核心、最关键的**概念组**。每个概念组代表一个独立的检索维度，旨在全面捕捉用户意图，无论其属于临床研究、基础研究还是交叉学科领域。

        #### **概念组识别指南（请举一反三）**

        **1. 核心主题/疾病概念组 (Core Subject / Disease Group):**
           - **定义**: 查询的核心研究对象。这通常是疾病、生物实体、特定人群、关键分子、科学问题或一种现象。
           - **关键词**:
             - **疾病/症状**: "癫痫"、"高血压"、"抑郁症"、"阿尔兹海默病"、"脓毒症"、"急性肾损伤"
             - **人群**: "成人"、"儿童"、"孕妇"、"老年患者"、"免疫缺陷人群"、"术后患者"
             - **生物实体/分子**: "皮肌炎患者"、"肿瘤微环境"、"基因敲除小鼠"、"T细胞"、"p53基因"、"外泌体"、"肠道菌群"
             - **医工/技术主题**: "纳米材料"、"机器学习算法"、"MRI影像"、"可穿戴设备"
           - **示例**:
             - 查询: "评估IVIG治疗皮肌炎的疗效" → `皮肌炎`
             - 查询: "T细胞在肝癌免疫治疗中的作用机制" → `肝癌`、`T细胞`
             - 查询: "用于帕金森病诊断的MRI影像分析模型" → `帕金森病`、`MRI影像分析`
             - 查询: "肠道菌群失调与自闭症谱系障碍的关联" → `肠道菌群`、`自闭症谱系障碍`
             - 查询: "一种新型水凝胶在创面修复中的应用" → `水凝胶`、`创面修复`

        **2. 干预/暴露/技术概念组 (Intervention / Exposure / Technology Group):**
           - **定义**: 施加于核心主题上的具体措施、暴露因素、研究技术、诊断方法或关键变量。
           - **关键词**:
             - **治疗/药物**: "IVIG"、"靶向治疗"、"免疫检查点抑制剂"、"阿司匹林"、"中药复方"
             - **非药物干预**: "行为干预"、"康复训练"、"针灸"、"正念疗法"、"健康教育"
             - **暴露因素**: "空气污染"、"吸烟"、"高脂饮食"、"农药暴露"、"职业压力"
             - **关键技术/方法**: "CRISPR-Cas9"、"超声造影"、"深度学习"、"单细胞测序"、"聚合酶链式反应(PCR)"、"质谱分析"
           - **示例**:
             - 查询: "评估IVIG治疗皮肌炎的疗效" → `IVIG`
             - 查询: "服务提供、行为干预和自我管理对成人癫痫的影响" → `服务提供、行为干预、自我管理`
             - 查询: "利用CRISPR技术研究p53基因功能" → `CRISPR技术`
             - 查询: "高盐饮食对小鼠肾脏纤维化的影响" → `高盐饮食`
             - 查询: "通过fMRI技术探究冥想对大脑功能连接的影响" → `fMRI技术`、`冥想`

        **3. 结局/应用/机制概念组 (Outcome / Application / Mechanism Group):**
           - **定义**: 研究希望观察到的结果、应用目标、或希望阐明的生物学/技术机制。
           - **关键词**:
             - **临床结局**: "疗效"、"生活质量"、"癫痫控制"、"预后"、"复发率"、"生存期"、"副作用"
             - **诊断/评估**: "诊断准确性"、"灵敏度与特异性"、"生物标志物"、"风险评估"
             - **机制/过程**: "信号通路"、"分子机制"、"基因表达"、"细胞凋亡"、"免疫应答"
             - **应用/性能**: "生物相容性"、"药物递送效率"、"算法性能"、"临床转化"
           - **示例**:
             - 查询: "评估IVIG治疗皮肌炎的疗效" → `疗效`
             - 查询: "T细胞在肝癌免疫治疗中的作用机制" → `作用机制`
             - 查询: "用于帕金森病诊断的MRI影像分析模型" → `诊断`
             - 查询: "血清MicroRNA-21作为胃癌早期筛查的生物标志物" → `生物标志物`、`早期筛查`
             - 查询: "探讨STAT3信号通路在肺动脉高压中的作用" → `STAT3信号通路`

        **4. 研究类型/设计概念组 (Study Type / Design Group):** (可选，仅当用户明确指定时提取)
           - **定义**: 用户明确限定的研究方法或证据级别。
           - **关键词**: "RCT"、"随机对照试验"、"系统评价"、"Meta分析"、"动物实验"、"队列研究"、"病例对照研究"、"体外研究"、"横断面研究"、"综述"。
           - **示例**:
             - 查询: "关于二甲双胍治疗2型糖尿病的随机对照试验" → `随机对照试验 (RCT)`
             - 查询: "儿童哮喘与室内过敏原暴露关系的前瞻性队列研究" → `前瞻性队列研究`
             - 查询: "间充质干细胞治疗膝关节炎的有效性Meta分析" → `Meta分析`

        ---

        **第二步：逻辑关系判定 (Logical Relationship Determination)**

        分析各概念组之间的关系，确定使用AND还是OR连接：

        **关键规则**：
        1. **并列关系 → 使用OR**：
           - 如果用户查询中出现"A、B和C"或"A, B, and C"，这些是**并列的可选项**
           - 它们应该在**同一个概念组内**，用OR连接
           - 示例："服务提供、行为干预、自我管理" → (service delivery OR behavioral intervention OR self-management)

        2. **不同维度 → 使用AND**：
           - 不同概念组之间（如疾病 AND 干预 AND 结局）用AND连接
           - 示例：(癫痫) AND (服务提供 OR 行为干预) AND (生活质量)

        3. **避免过度使用AND**：
           - 如果用户只提到一个核心主题（如"癫痫的护理干预"），不要强行添加过多AND限制
           - 优先使用OR扩大范围，谨慎使用AND缩小范围

        **逻辑框架示例**：
        - 用户查询："服务提供、行为干预和自我管理对成人癫痫的影响"
          → 逻辑框架：(成人癫痫) AND (服务提供 OR 行为干预 OR 自我管理) AND (影响/效果)

        ---

        **第三步：两层关键词扩展 (Two-Layer Keyword Expansion)**

        对每个概念组进行两层扩展：

        **第一层：同义词/相关术语扩展**
        - 为每个核心概念添加2-3个直接同义词、缩写、MeSH术语
        - 示例：
          - "癫痫" → "epilepsy"[mesh] OR "seizures"[mesh] OR "epilepsy"[tiab]
          - "IVIG" → "intravenous immune globulin"[tiab] OR "IVIG"[tiab] OR "intravenous immunoglobulin"[tiab]

        **第二层：实例扩展（关键！）**
        - **如果某个概念是一个类别**（如"靶向治疗"、"行为干预"、"免疫抑制剂"），必须列出该类别下**至少5-10个具体的、常见的实例**
        - 这些实例用OR连接

        **实例扩展示例库（请参考以下示例进行举一反三）**：

        **领域1：药物治疗研究**

        **示例1.1 - 免疫抑制剂类别**
        - 用户查询："免疫抑制剂治疗皮肌炎"
        - ✅ 正确做法：
          ```
          ("immunosuppressive agents"[tiab] OR "immunosuppressants"[tiab] OR
           "methotrexate"[tiab] OR "azathioprine"[tiab] OR "cyclosporine"[tiab] OR
           "mycophenolate"[tiab] OR "tacrolimus"[tiab] OR "cyclophosphamide"[tiab])
          ```

        **示例1.2 - 靶向生物制剂类别**
        - 用户查询："靶向治疗特发性炎性肌病"
        - ✅ 正确做法：
          ```
          ("targeted therapy"[tiab] OR "biologics"[tiab] OR
           "rituximab"[tiab] OR "abatacept"[tiab] OR "tocilizumab"[tiab] OR
           "belimumab"[tiab] OR "lenabasum"[tiab] OR "IMO-8400"[tiab] OR
           "anti-TNF"[tiab] OR "infliximab"[tiab])
          ```

        **示例1.3 - 免疫球蛋白治疗**
        - 用户查询："IVIG治疗神经系统疾病"
        - ✅ 正确做法：
          ```
          ("IVIG"[tiab] OR "intravenous immune globulin"[tiab] OR
           "intravenous immunoglobulin"[tiab] OR "immunoglobulin therapy"[tiab] OR
           "IVIg"[tiab] OR "immune globulin"[mesh])
          ```

        ---

        **领域2：临床干预与护理研究**

        **示例2.1 - 行为干预类别**
        - 用户查询："行为干预对癫痫的影响"
        - ✅ 正确做法：
          ```
          ("behavioral intervention"[tiab] OR "behavioral therapy"[tiab] OR
           "cognitive behavioral therapy"[tiab] OR "CBT"[tiab] OR
           "relaxation"[tiab] OR "meditation"[tiab] OR "mindfulness"[tiab] OR
           "biofeedback"[tiab] OR "stress management"[tiab] OR "yoga"[tiab])
          ```

        **示例2.2 - 服务提供模式类别**
        - 用户查询："服务提供对癫痫患者的影响"
        - ✅ 正确做法：
          ```
          ("service delivery"[tiab] OR "healthcare delivery"[tiab] OR
           "pharmaceutical care"[tiab] OR "nurse specialist"[tiab] OR
           "epilepsy nurse"[tiab] OR "nurse-led clinic"[tiab] OR
           "home-based care"[tiab] OR "clinic-based care"[tiab] OR
           "telemedicine"[tiab] OR "telehealth"[tiab] OR "mHealth"[tiab])
          ```

        **示例2.3 - 自我管理干预类别**
        - 用户查询："自我管理对慢性病的影响"
        - ✅ 正确做法：
          ```
          ("self-management"[tiab] OR "self-care"[tiab] OR
           "patient education"[mesh] OR "health education"[tiab] OR
           "self-monitoring"[tiab] OR "medication adherence"[tiab] OR
           "lifestyle modification"[tiab] OR "disease management"[tiab])
          ```

        ---

        **领域3：诊断与筛查研究**

        **示例3.1 - 焦虑筛查工具类别**
        - 用户查询："焦虑筛查工具的准确性"
        - ✅ 正确做法：
          ```
          ("anxiety screening"[tiab] OR "anxiety scale"[tiab] OR
           "HADS"[tiab] OR "HADS-A"[tiab] OR "Hospital Anxiety and Depression Scale"[tiab] OR
           "GAD-7"[tiab] OR "Generalized Anxiety Disorder-7"[tiab] OR
           "Beck Anxiety Inventory"[tiab] OR "BAI"[tiab] OR
           "State-Trait Anxiety Inventory"[tiab] OR "STAI"[tiab])
          ```

        **示例3.2 - 影像诊断技术类别**
        - 用户查询："影像诊断脑肿瘤的准确性"
        - ✅ 正确做法：
          ```
          ("imaging"[tiab] OR "diagnostic imaging"[mesh] OR
           "MRI"[tiab] OR "magnetic resonance imaging"[tiab] OR
           "CT"[tiab] OR "computed tomography"[tiab] OR
           "PET"[tiab] OR "positron emission tomography"[tiab] OR
           "fMRI"[tiab] OR "functional MRI"[tiab])
          ```

        ---

        **领域4：分子与细胞生物学研究**

        **示例4.1 - 胶质细胞类别**
        - 用户查询："胶质细胞在脊髓损伤中的作用"
        - ✅ 正确做法：
          ```
          ("glial cells"[mesh] OR "glia"[tiab] OR
           "astrocyte"[mesh] OR "astrocytes"[tiab] OR "GFAP"[tiab] OR
           "microglia"[mesh] OR "microglial cells"[tiab] OR "Iba1"[tiab] OR
           "oligodendrocyte"[mesh] OR "oligodendrocytes"[tiab] OR "NG2"[tiab])
          ```

        **示例4.2 - 免疫细胞类别**
        - 用户查询："免疫细胞在肿瘤微环境中的作用"
        - ✅ 正确做法：
          ```
          ("immune cells"[tiab] OR "leukocytes"[mesh] OR
           "T cells"[mesh] OR "T lymphocytes"[tiab] OR "CD4"[tiab] OR "CD8"[tiab] OR
           "B cells"[mesh] OR "B lymphocytes"[tiab] OR
           "macrophages"[mesh] OR "tumor-associated macrophages"[tiab] OR "TAM"[tiab] OR
           "dendritic cells"[mesh] OR "NK cells"[tiab] OR "natural killer cells"[tiab])
          ```

        **示例4.3 - 信号通路类别**
        - 用户查询："信号通路在癌症中的作用"
        - ✅ 正确做法：
          ```
          ("signaling pathway"[tiab] OR "signal transduction"[mesh] OR
           "MAPK pathway"[tiab] OR "ERK pathway"[tiab] OR
           "PI3K/AKT pathway"[tiab] OR "PI3K-AKT"[tiab] OR
           "Wnt signaling"[tiab] OR "Wnt pathway"[tiab] OR
           "Notch signaling"[tiab] OR "JAK/STAT pathway"[tiab] OR
           "NF-kappa B"[tiab] OR "mTOR pathway"[tiab])
          ```

        ---

        **领域5：基因与分子技术研究**

        **示例5.1 - 基因编辑技术类别**
        - 用户查询："基因编辑技术在疾病治疗中的应用"
        - ✅ 正确做法：
          ```
          ("gene editing"[tiab] OR "genome editing"[tiab] OR
           "CRISPR"[tiab] OR "CRISPR-Cas9"[tiab] OR "CRISPR/Cas9"[tiab] OR
           "TALEN"[tiab] OR "transcription activator-like effector nuclease"[tiab] OR
           "zinc finger nuclease"[tiab] OR "ZFN"[tiab] OR
           "base editing"[tiab] OR "prime editing"[tiab])
          ```

        **示例5.2 - 测序技术类别**
        - 用户查询："测序技术在癌症研究中的应用"
        - ✅ 正确做法：
          ```
          ("sequencing"[tiab] OR "DNA sequencing"[tiab] OR
           "next-generation sequencing"[tiab] OR "NGS"[tiab] OR
           "whole genome sequencing"[tiab] OR "WGS"[tiab] OR
           "whole exome sequencing"[tiab] OR "WES"[tiab] OR
           "RNA sequencing"[tiab] OR "RNA-seq"[tiab] OR
           "single-cell sequencing"[tiab] OR "scRNA-seq"[tiab])
          ```

        ---

        **领域6：医疗器械与技术研究**

        **示例6.1 - 脑机接口技术类别**
        - 用户查询："脑机接口在癫痫监测中的应用"
        - ✅ 正确做法：
          ```
          ("brain-computer interface"[tiab] OR "BCI"[tiab] OR
           "brain-machine interface"[tiab] OR "BMI"[tiab] OR
           "EEG-based BCI"[tiab] OR "electroencephalography BCI"[tiab] OR
           "invasive BCI"[tiab] OR "non-invasive BCI"[tiab] OR
           "P300"[tiab] OR "SSVEP"[tiab] OR "motor imagery"[tiab])
          ```

        **示例6.2 - 人工智能技术类别**
        - 用户查询："AI在医学影像诊断中的应用"
        - ✅ 正确做法：
          ```
          ("artificial intelligence"[tiab] OR "AI"[tiab] OR
           "machine learning"[tiab] OR "deep learning"[tiab] OR
           "convolutional neural network"[tiab] OR "CNN"[tiab] OR
           "neural network"[tiab] OR "random forest"[tiab] OR
           "support vector machine"[tiab] OR "SVM"[tiab])
          ```

        ---

        **领域7：公共卫生与流行病学研究**

        **示例7.1 - 疾病负担指标类别**
        - 用户查询："癫痫的疾病负担"
        - ✅ 正确做法：
          ```
          ("disease burden"[tiab] OR "burden of disease"[tiab] OR
           "prevalence"[tiab] OR "incidence"[tiab] OR
           "DALY"[tiab] OR "disability-adjusted life years"[tiab] OR
           "YLD"[tiab] OR "years lived with disability"[tiab] OR
           "mortality"[tiab] OR "morbidity"[tiab])
          ```

        ---

        **如何使用这些示例**：

        1. **识别类别概念**：判断用户查询中的概念是否是一个"类别"（如"药物"、"干预"、"工具"、"细胞"、"技术"）
        2. **参考对应领域示例**：找到最相似的领域示例
        3. **举一反三**：根据示例的模式，为当前查询生成具体实例
        4. **保持数量适中**：每个类别列出5-10个具体实例即可，不要过度扩展

        **关键原则**：
        - ✅ 类别概念 → 必须列出具体实例
        - ✅ 具体概念 → 只需同义词扩展
        - ✅ 并列关系 → 用OR连接
        - ✅ 不同维度 → 用AND连接

        ---

        **第四步：构建最终检索式**

        将上述三步的结果组合成PubMed检索式（我希望检索式的连接方式不单单的OR，而是OR和AND的组合，起码整个检索式要出现至少一个AND）：

        **检索式结构**：
        ```
        (概念组1的关键词，用OR连接) AND
        (概念组2的关键词，用OR连接，包含具体实例) AND
        (概念组3的关键词，用OR连接)
        ```

        **质量标准**：
        ✅ 必须使用括号清晰分隔每个概念组
        ✅ 并列概念必须用OR连接
        ✅ 不同维度的概念组用AND连接
        ✅ 如果概念是类别，必须包含具体实例
        ✅ 每个概念最多3-4个同义词（避免过度扩展）
        ✅ 优先使用[mesh]和[tiab]字段
        ✅ 总长度控制在1000字符以内

        ---

        **PubMed标准字段标签（只能使用以下字段）：**
        - [Title/Abstract] 或 [tiab] - 标题和摘要
        - [MeSH Terms] 或 [mesh] - 医学主题词
        - [Title] 或 [ti] - 仅标题
        - [Publication Type] 或 [pt] - 发表类型
        - [Text Word] 或 [tw] - 文本词

        **严禁使用的错误字段标签：**
        - [Supplementary Concept] ❌
        - [Chemical] ❌
        - [Keyword] ❌

        **输出检索式范例 (请举一反三)**：

        - **用户查询**: "评估分子诊断方法在新生儿细菌性和真菌性脓毒症中的诊断准确性及亚组分析"
        - **输出范例**:
        ("Infant, Newborn"[MeSH Terms] OR "Intensive Care, Neonatal"[MeSH Terms] OR "Intensive Care Units, Neonatal"[MeSH Terms] OR "Gestational Age"[MeSH Terms] OR babe[Title/Abstract] OR babes[Title/Abstract] OR baby*[Title/Abstract] OR babies[Title/Abstract] OR "gestational age"[Title/Abstract] OR infant*[Title/Abstract] OR infantile[Title/Abstract] OR infancy[Title/Abstract] OR "low birth weight"[Title/Abstract] OR "low birthweight"[Title/Abstract] OR neonat*[Title/Abstract] OR "neo-nat*"[Title/Abstract] OR newborn*[Title/Abstract] OR "new born"[Title/Abstract] OR "newly born"[Title/Abstract] OR premature[Title/Abstract] OR "pre-mature"[Title/Abstract] OR prematures[Title/Abstract] OR prematurity[Title/Abstract] OR "pre-maturity"[Title/Abstract] OR preterm[Title/Abstract] OR preterms[Title/Abstract] OR "pre term"[Title/Abstract] OR preemie[Title/Abstract] OR preemies[Title/Abstract] OR premies[Title/Abstract] OR premie[Title/Abstract] OR VLBW[Title/Abstract] OR VLBWI[Title/Abstract] OR "VLBW-I"[Title/Abstract] OR VLBWs[Title/Abstract] OR LBW[Title/Abstract] OR LBWI[Title/Abstract] OR LBWs[Title/Abstract] OR ELBW[Title/Abstract] OR ELBWI[Title/Abstract] OR ELBWs[Title/Abstract] OR NICU[Title/Abstract] OR NICUs[Title/Abstract]) AND ("Nucleic Acids"[MeSH Major Topic] OR "nucleic acid*"[Title/Abstract] OR "Blood Culture"[MeSH Major Topic] OR "blood culture"[Title/Abstract] OR bloodculture[Title/Abstract] OR "culture based"[Title/Abstract] OR (molecular*[Title/Abstract] AND (assay*[Title/Abstract] OR test*[Title/Abstract] OR system*[Title/Abstract] OR diagnostic*[Title/Abstract] OR tool*[Title/Abstract])) OR "polymerase chain reaction*"[Title/Abstract] OR PCR[Title/Abstract] OR rt-PCR[Title/Abstract] OR qPCR[Title/Abstract] OR mNGS[Title/Abstract]) AND ("Neonatal Sepsis"[MeSH Terms] OR "Bacterial Infections"[MeSH Major Topic] OR sepsis[Title/Abstract] OR septicemia*[Title/Abstract] OR pyaemia*[Title/Abstract] OR pyemia*[Title/Abstract] OR pyohemia*[Title/Abstract] OR ((blood*[Title/Abstract] OR bacterial[Title/Abstract] OR bacteria[Title/Abstract] OR septic*[Title/Abstract] OR fungal[Title/Abstract] OR fungi[Title/Abstract] OR CNS[Title/Abstract]) AND (infect*[Title/Abstract] OR poisoning*[Title/Abstract])) OR "Candida species"[Title/Abstract] OR "candida albicans"[Title/Abstract] OR Candidiasis[Title/Abstract] OR ((bacteria*[Title/Abstract] OR bacteremia[Title/Abstract] OR fungi[Title/Abstract]) AND culture*[Title/Abstract]))

        - **用户查询**: "评估随机对照试验中匹配靶向疗法对晚期癌症患者的益处和危害"
        - **输出范例**:
        ("High-Throughput Nucleotide Sequencing"[MeSH Terms] OR "Molecular Sequence Annotation"[MeSH Terms] OR "next generation"[Title/Abstract] OR "next-gen"[Title/Abstract] OR NGS[Title/Abstract] OR "Sequence Analysis, DNA"[MeSH Terms]) AND ("Molecular Targeted Therapy"[MeSH Terms] OR ((match*[Title/Abstract] OR "non-match*"[Title/Abstract] OR molecular*[Title/Abstract] OR target*[Title/Abstract]) AND (therap*[Title/Abstract] OR group*[Title/Abstract] OR mutation*[Title/Abstract] OR compound*[Title/Abstract])) OR ((molecular*[Title/Abstract] OR tumor*[Title/Abstract] OR tumour*[Title/Abstract]) AND (marker*[Title/Abstract] OR mutation*[Title/Abstract] OR screen*[Title/Abstract] OR understanding*[Title/Abstract] OR alteration*[Title/Abstract] OR subtype*[Title/Abstract])) OR "diagnostic precision"[Title/Abstract] OR ((action*[Title/Abstract] OR target*[Title/Abstract]) AND mutation*[Title/Abstract]) OR "genetic alteration*"[Title/Abstract] OR ((personal*[Title/Abstract] OR individual*[Title/Abstract]) AND (treatment*[Title/Abstract] OR therap*[Title/Abstract]))) AND ("Neoplasms"[MeSH Terms] OR cancer*[Title/Abstract] OR tumor*[Title/Abstract] OR tumour*[Title/Abstract] OR neoplas*[Title/Abstract] OR malignan*[Title/Abstract] OR carcinoma*[Title/Abstract] OR adenocarcinoma*[Title/Abstract] OR choriocarcinoma*[Title/Abstract] OR leukemia*[Title/Abstract] OR leukaemia*[Title/Abstract] OR metastat*[Title/Abstract] OR sarcoma*[Title/Abstract] OR teratoma*[Title/Abstract] OR oncolog*[Title/Abstract])

        - **用户查询**: "硫唑嘌呤和6-巯基嘌呤维持治疗溃疡性结肠炎缓解的有效性和安全性"
        - **输出范例**:
        (anti-metabolite*[Text Word] OR antimetabolite*[Text Word] OR AZA[Text Word] OR azathioprine[Text Word] OR "6-mercaptopurine"[Text Word] OR mercaptopurine[Text Word] OR "6-MP"[Text Word] OR 6MP[Text Word] OR "Azathioprine"[Mesh]) AND ("Ulcerative Colitis"[Mesh] OR "ulcerative colitis"[Text Word] OR "inflammatory bowel disease*"[Text Word] OR IBD[Text Word])

        - **用户查询**: "利尿剂在急性肾损伤（AKI）预防和治疗中的益处与危害"
        - **输出范例**:
        ("Acute Kidney Injury"[MeSH Terms] OR "acute kidney failure"[Title/Abstract] OR "acute renal failure"[Title/Abstract] OR "acute kidney injur*"[Title/Abstract] OR "acute renal injur*"[Title/Abstract] OR "acute kidney insufficie*"[Title/Abstract] OR "acute renal insufficie*"[Title/Abstract] OR "acute tubular necrosis"[Title/Abstract] OR ARI[Title/Abstract] OR AKI[Title/Abstract] OR ARF[Title/Abstract] OR AKF[Title/Abstract] OR ATN[Title/Abstract]) AND ("Diuretics"[MeSH Terms] OR "Natriuretic Peptides"[MeSH Terms] OR diuretic*[Title/Abstract] OR "atrial natriuretic peptide*"[Title/Abstract] OR anp[Title/Abstract] OR "brain natriuretic peptide*"[Title/Abstract] OR bnp[Title/Abstract] OR acetazolamide[Title/Abstract] OR amiloride[Title/Abstract] OR bendroflumethiazide[Title/Abstract] OR bumetanide[Title/Abstract] OR chlorothiazide[Title/Abstract] OR clopamide[Title/Abstract] OR cyclopenthiazide[Title/Abstract] OR "ethacrynic acid"[Title/Abstract] OR ethoxzolamide[Title/Abstract] OR furosemide[Title/Abstract] OR hydrochlorothiazide[Title/Abstract] OR hydroflumethiazide[Title/Abstract] OR Indapamide[Title/Abstract] OR mefruside[Title/Abstract] OR methazolamide[Title/Abstract] OR methyclothiazide[Title/Abstract] OR metolazone[Title/Abstract] OR muzolimine[Title/Abstract] OR polythiazide[Title/Abstract] OR "potassium citrate"[Title/Abstract] OR spironolactone[Title/Abstract] OR ticrynafen[Title/Abstract] OR Torsemide[Title/Abstract] OR triamterene[Title/Abstract] OR trichlormethiazide[Title/Abstract] OR xipamide[Title/Abstract] OR Isosorbide[Title/Abstract] OR mannitol[Title/Abstract] OR "canrenoic acid"[Title/Abstract] OR canrenone[Title/Abstract] OR eplerenone[Title/Abstract] OR "Tolvaptan"[Supplementary Concept] OR tolvaptan[Title/Abstract])

        - **用户查询**: "胰腺术后常规腹腔引流的益处、危害及拔管时机评估"
        - **输出范例**:
        (("Pancreas"[MeSH Terms] OR pancrea*[Title/Abstract]) AND ("General Surgery"[MeSH Terms] OR resect*[Title/Abstract] OR surger*[Title/Abstract] OR surgical[Title/Abstract] OR operat*[Title/Abstract] OR postoperat*[Title/Abstract] OR "Pancreatectomy"[MeSH Terms] OR pancreatectom*[Title/Abstract] OR "Pancreaticoduodenectomy"[MeSH Terms] OR duodenopancreatectom*[Title/Abstract] OR pancreatoduodenectom*[Title/Abstract] OR pancreaticogastrostom*[Title/Abstract] OR whipple[Title/Abstract] OR "Pancreaticojejunostomy"[MeSH Terms] OR pancreatojejunostom*[Title/Abstract] OR pancreaticojejunostom*[Title/Abstract] OR (pancrea*[Title/Abstract] AND (duodenectom*[Title/Abstract] OR jejunostom*[Title/Abstract] OR gastrostom*[Title/Abstract])) OR "pancreaticojejunal anastomosis"[Title/Abstract] OR "jejunopancreatic anastomosis"[Title/Abstract] OR "jejuno-pancreatic anastomosis"[Title/Abstract])) AND ("Drainage"[MeSH Terms] OR drain*[Title/Abstract] OR suction*[Title/Abstract] OR aspirat*[Title/Abstract] OR paracentesis[Title/Abstract])

        - **用户查询**: "肿瘤坏死因子抑制剂（TNFi）治疗幼年特发性关节炎（JIA）的益处和危害"
        - **输出范例**:
        (("Arthritis, Juvenile"[MeSH Terms] OR "juvenile arthritis*"[Title/Abstract] OR JIA[Title/Abstract])) AND (("Tumor Necrosis Factor-alpha"[MeSH Terms] OR "Tumor Necrosis Factor*"[Title/Abstract] OR "Etanercept"[MeSH Terms] OR etanercept[Title/Abstract] OR enbrel[Title/Abstract] OR "Infliximab"[MeSH Terms] OR infliximab[Title/Abstract] OR remicade[Title/Abstract] OR "Adalimumab"[MeSH Terms] OR adalimumab[Title/Abstract] OR humira[Title/Abstract] OR "Golimumab"[Supplementary Concept] OR Golimumab[Title/Abstract] OR Simponi[Title/Abstract] OR "Certolizumab Pegol"[Supplementary Concept] OR Certolizumab[Title/Abstract] OR Cimzia[Title/Abstract] OR "infliximab biosimilar*"[Title/Abstract] OR "adalimumab biosimilar*"[Title/Abstract] OR "etanercept biosimilar*"[Title/Abstract] OR "Golimumab biosimilar*"[Title/Abstract] OR "Certolizumab biosimilar*"[Title/Abstract]))

        - **用户查询**: "疑似阻塞性睡眠呼吸暂停患者中有限导联睡眠监测与多导睡眠图指导治疗的临床结局对比"
        - **输出范例**:
        ("Polysomnography"[MeSH Terms] OR "diagnosis"[Subheading] OR diagn*[Title/Abstract] OR polysomnograph*[Title/Abstract] OR PSG[Title/Abstract] OR "limited channel sleep stud*"[Title/Abstract] OR "home sleep test"[Title/Abstract]) AND ("apnoea"[Title/Abstract] OR "apnea"[MeSH Terms] OR hypopnea[Title/Abstract] OR hypopnoea[Title/Abstract] OR OSAS[Title/Abstract] OR OSAHS[Title/Abstract] OR ((OSA[Title/Abstract] OR SHS[Title/Abstract]) AND sleep[Title/Abstract]))

        - **用户查询**: "单孔与多孔腹腔镜阑尾切除术治疗急性阑尾炎的疗效对比"
        - **输出范例**:
        ("Appendix"[MeSH Terms] OR "Appendicitis"[MeSH Terms] OR "Appendectomy"[MeSH Terms] OR appendec*[Title/Abstract] OR appendicec*[Title/Abstract] OR appendicit*[Title/Abstract]) AND ("Laparoscopy"[MeSH Terms] OR laporoscop*[Title/Abstract] OR laparoscop*[Title/Abstract] OR "minimal* invasiv*"[Title/Abstract] OR celioscop*[Title/Abstract] OR peritoneoscop*[Title/Abstract] OR (("single port"[Title/Abstract] OR singleport[Title/Abstract] OR "single incision"[Title/Abstract] OR singleincision[Title/Abstract] OR "single site"[Title/Abstract] OR singlesite[Title/Abstract] OR SILS[Title/Abstract] OR SILA[Title/Abstract]) AND append*[Title/Abstract]))

        - **用户查询**: "超声引导与解剖标志引导下股总动脉穿刺的有效性和安全性对比"
        - **输出范例**:
        ("Femoral Artery"[MeSH Terms] OR femoral*[Title/Abstract] OR CFA[Title/Abstract]) AND ("Ultrasonography, Interventional"[MeSH Terms] OR ultrasonograph*[Title/Abstract] OR Ultrasound*[Title/Abstract]) AND ("Punctures"[MeSH Terms] OR "Catheterization, Peripheral"[MeSH Terms] OR puncture*[Title/Abstract] OR Cathlon[Title/Abstract] OR Venflon[Title/Abstract] OR cannula*[Title/Abstract] OR ((Catheter*[Title/Abstract] OR line[Title/Abstract] OR access[Title/Abstract]) AND peripher*[Title/Abstract]))

        - **用户查询**: "虚拟现实技术在脑卒中患者上肢功能和活动能力康复中的应用效果"
        - **输出范例**:
        ("Cerebrovascular Disorders"[MeSH Terms] OR "Basal Ganglia Cerebrovascular Disease"[MeSH Terms] OR "Brain Ischemia"[MeSH Terms] OR "Carotid Artery Diseases"[MeSH Terms] OR "Intracranial Arterial Diseases"[MeSH Terms] OR "Intracranial Arteriovenous Malformations"[MeSH Terms] OR "Intracranial Embolism and Thrombosis"[MeSH Terms] OR "Intracranial Hemorrhages"[MeSH Terms] OR "Stroke"[MeSH Terms] OR "Brain Infarction"[MeSH Terms] OR "Brain Injuries"[MeSH Terms] OR "Brain Injury, Chronic"[MeSH Terms] OR stroke*[Title/Abstract] OR cva[Title/Abstract] OR poststroke[Title/Abstract] OR "post-stroke"[Title/Abstract] OR cerebrovasc*[Title/Abstract] OR "cerebral vascular"[Title/Abstract] OR ((cerebral[Title/Abstract] OR cerebellar[Title/Abstract] OR brain*[Title/Abstract] OR vertebrobasilar[Title/Abstract]) AND (infarct*[Title/Abstract] OR ischemi*[Title/Abstract] OR ischaemi*[Title/Abstract] OR thrombo*[Title/Abstract] OR emboli*[Title/Abstract] OR apoplexy[Title/Abstract])) OR ((cerebral[Title/Abstract] OR brain[Title/Abstract] OR subarachnoid[Title/Abstract]) AND (haemorrhage[Title/Abstract] OR hemorrhage[Title/Abstract] OR haematoma[Title/Abstract] OR hematoma[Title/Abstract] OR bleed*[Title/Abstract])) OR "Hemiplegia"[MeSH Terms] OR "Paresis"[MeSH Terms] OR hempar*[Title/Abstract] OR hemipleg*[Title/Abstract] OR paresis[Title/Abstract] OR paretic[Title/Abstract] OR "brain injur*"[Title/Abstract] OR "Gait Disorders, Neurologic"[MeSH Terms]) AND ("User-Computer Interface"[MeSH Terms] OR "Computers"[MeSH Terms] OR "Microcomputers"[MeSH Terms] OR "Computer Systems"[MeSH Terms] OR "Software"[MeSH Terms] OR "Computer Simulation"[MeSH Terms] OR "Computer-Assisted Instruction"[MeSH Terms] OR "Therapy, Computer-Assisted"[MeSH Terms] OR "Computer Graphics"[MeSH Terms] OR "Video Games"[MeSH Terms] OR "Touch"[MeSH Major Topic] OR "virtual reality*"[Title/Abstract] OR "virtual-reality*"[Title/Abstract] OR VR[Title/Abstract] OR (virtual[Title/Abstract] AND (environment*[Title/Abstract] OR object*[Title/Abstract] OR world*[Title/Abstract] OR treatment*[Title/Abstract] OR system*[Title/Abstract] OR program*[Title/Abstract] OR rehabilitation*[Title/Abstract] OR therap*[Title/Abstract] OR driving[Title/Abstract] OR drive*[Title/Abstract] OR car[Title/Abstract] OR tunnel[Title/Abstract] OR vehicle[Title/Abstract])) OR (computer[Title/Abstract] AND (simulat*[Title/Abstract] OR graphic*[Title/Abstract] OR game*[Title/Abstract] OR interact*[Title/Abstract])) OR (computer[Title/Abstract] AND assist*[Title/Abstract] AND (therap*[Title/Abstract] OR treat*[Title/Abstract])) OR (computer[Title/Abstract] AND generat*[Title/Abstract] AND (environment*[Title/Abstract] OR object*[Title/Abstract])) OR "video game*"[Title/Abstract] OR "video gaming"[Title/Abstract] OR "gaming console*"[Title/Abstract] OR "interactive game"[Title/Abstract] OR "interactive gaming"[Title/Abstract] OR "Nintendo Wii"[Title/Abstract] OR "gaming program*"[Title/Abstract] OR haptics[Title/Abstract] OR "haptic device*"[Title/Abstract] OR (simulat*[Title/Abstract] AND (environment*[Title/Abstract] OR object*[Title/Abstract] OR event*[Title/Abstract] OR driving[Title/Abstract] OR drive*[Title/Abstract] OR car[Title/Abstract] OR tunnel[Title/Abstract] OR vehicle[Title/Abstract])) OR (user[Title/Abstract] AND computer[Title/Abstract] AND interface[Title/Abstract]))
        
        
        **绝对禁止：**
        - 严禁在生成的PubMed检索式中包含任何与JCR分区、中科院分区、影响因子(IF)、引用次数、H-index或任何其他期刊评价指标相关的信息
        - **严禁添加任何时间限制**（如 `[dp]`、`[pdat]`、`2021:2024[dp]` 等）。

        ---

        **现在，请为用户查询"{user_query}"生成检索式**

        **直接输出检索式（不要包含任何解释）：**
        """

    @staticmethod
    def get_refine_pubmed_query_prompt(user_query: str, failed_query: str, previous_count: int = 0, attempt_number: int = 1, current_results_count: int = 0, max_attempts: int = 50, target_articles: int = 300) -> str:
        # 🔥 渐进式精准扩展策略
        # 根据轮次和文献数量动态决定策略，支持用户自定义参数

        # 📊 动态计算轮次范围（基于用户设置的最大轮次）
        # 默认50轮的分配：1-10轮(20%), 11-20轮(20%), 21-30轮(20%), 31-40轮(20%), 41-50轮(20%)
        stage1_end = int(max_attempts * 0.2)    # 默认50*0.2=10轮：同义词扩展阶段
        stage2_end = int(max_attempts * 0.4)    # 默认50*0.4=20轮：相关术语扩展阶段
        stage3_end = int(max_attempts * 0.6)    # 默认50*0.6=30轮：数量驱动策略1阶段
        stage4_end = int(max_attempts * 0.8)    # 默认50*0.8=40轮：数量驱动策略2阶段
        # 剩余20%轮次(41-50轮)：最终策略阶段

        # 📈 动态计算文献数量阈值（基于用户设置的目标文献数）
        # 默认300篇的阈值：50篇(17%), 120篇(40%), 200篇(67%), 250篇(83%), 20篇(7%)
        low_threshold = int(target_articles * 0.17)      # 默认300*0.17≈50篇：触发向上扩展的低阈值
        mid_threshold1 = int(target_articles * 0.4)      # 默认300*0.4=120篇：第二阶段的低阈值
        mid_threshold2 = int(target_articles * 0.67)     # 默认300*0.67≈200篇：中等阈值
        high_threshold = int(target_articles * 0.83)     # 默认300*0.83≈250篇：高阈值，触发精确化
        very_low_threshold = int(target_articles * 0.067) # 默认300*0.067≈20篇：极低阈值，触发最大化扩展

        # 添加检索式长度控制
        if len(failed_query) > 1500:
            strategy_instruction = f"""
            **第{attempt_number}轮检索优化 - 强制简化策略**

            **当前状态**: 检索式过于复杂(长度{len(failed_query)}字符)
            **策略要求**: 必须简化检索式

            **强制简化原则**:
            - 回归用户查询"{user_query}"的核心概念
            - 移除边缘相关的术语
            - 每个概念最多保留3个同义词
            - 总长度控制在1000字符以内
            - 保持最核心的概念组合
            """
        elif attempt_number <= stage1_end:
            # 🎯 第一阶段：同义词扩展（默认1-10轮，占总轮次的前20%）
            strategy_instruction = f"""
            **第{attempt_number}轮检索优化 - 同义词扩展**

            **当前状态**: 第{attempt_number}轮（第一阶段：1-{stage1_end}轮），已有{current_results_count}篇文献
            **扩展策略**: 添加核心概念的同义词，比如（请举一反三）：

            **疾病/病症的同义词**：
            - 核心概念：癫痫
              → 同义词：epilepsy, seizure disorder, convulsive disorder, epileptic seizure等等
            - 核心概念：皮肌炎
              → 同义词：dermatomyositis, DM, juvenile dermatomyositis, JDM等等
            - 核心概念：心力衰竭
              → 同义词：heart failure, cardiac failure, HF, congestive heart failure, CHF等等

            **药物/治疗的同义词**：
            - 核心概念：免疫抑制剂
              → 同义词：immunosuppressive agents, immunosuppressants, immunosuppressive drugs, immune suppressants等等
            - 核心概念：静脉注射免疫球蛋白
              → 同义词：intravenous immunoglobulin, IVIG, IVIg, intravenous immune globulin等等

            **研究方法的同义词**：
            - 核心概念：随机对照试验
              → 同义词：randomized controlled trial, RCT, randomised controlled trial（英式拼写）, randomized clinical trial等等
            - 核心概念：系统评价
              → 同义词：systematic review, systematic literature review, evidence synthesis等等

            **操作指南**：
            - 针对用户查询"{user_query}"的每个核心概念，添加2-3个直接同义词
            - 使用医学词典中的标准同义词和缩写
            - 优先使用MeSH术语的同义词
            - 每个概念最多3-4个同义词
            - 不限于上述例子，请举一反三
            - 所有同义词用OR连接
            - 保持检索式结构清晰
            """
        elif attempt_number <= stage2_end:
            # 🔍 第二阶段：实例补充 + 相关术语扩展（默认11-20轮，占总轮次的20%-40%）
            strategy_instruction = f"""
            **第{attempt_number}轮检索优化 - 实例补充 + 相关术语扩展**

            **当前状态**: 第{attempt_number}轮（第二阶段：{stage1_end+1}-{stage2_end}轮），已有{current_results_count}篇文献
            **扩展策略**: 补充具体实例，并添加相关术语

            **第一步：检查是否缺少具体实例（关键！）**

            检查当前检索式"{failed_query}"中是否存在**抽象的类别概念**但缺少**具体实例**，比如：

            **药物类别检查**：
            - 如果有"免疫抑制剂"、"immunosuppressive agents"，是否包含具体药物？
              → 应补充：methotrexate, azathioprine, cyclosporine, mycophenolate, tacrolimus等等
            - 如果有"靶向治疗"、"targeted therapy"、"biologics"，是否包含具体药物？
              → 应补充：rituximab, abatacept, tocilizumab, belimumab, infliximab等等
            - 如果有"IVIG"，是否包含所有表达方式？
              → 应补充：intravenous immune globulin, intravenous immunoglobulin, IVIg等等

            **干预类别检查**：
            - 如果有"行为干预"、"behavioral intervention"，是否包含具体方法？
              → 应补充：cognitive behavioral therapy, CBT, relaxation, meditation, mindfulness, biofeedback等等
            - 如果有"服务提供"、"service delivery"，是否包含具体模式？
              → 应补充：pharmaceutical care, nurse specialist, epilepsy nurse, nurse-led clinic, home-based care, telemedicine等等
            - 如果有"自我管理"、"self-management"，是否包含具体形式？
              → 应补充：patient education, self-monitoring, medication adherence, lifestyle modification等等

            **诊断工具检查**：
            - 如果有"焦虑筛查"、"anxiety screening"，是否包含具体工具？
              → 应补充：HADS, HADS-A, GAD-7, Beck Anxiety Inventory, BAI等等
            - 如果有"抑郁筛查"、"depression screening"，是否包含具体工具？
              → 应补充：PHQ-9, BDI, HADS-D, Hamilton Depression Rating Scale等等

            **细胞/分子检查**：
            - 如果有"胶质细胞"、"glial cells"，是否包含具体类型？
              → 应补充：astrocyte, GFAP, microglia, Iba1, oligodendrocyte等等
            - 如果有"免疫细胞"、"immune cells"，是否包含具体类型？
              → 应补充：T cells, B cells, macrophages, dendritic cells, NK cells等等

            **第二步：相关术语扩展**

            相关术语扩展是指添加与核心概念相关但不完全等同的术语（A 与 B 相关，但 A ≠ B），比如（请举一反三）：

            **疾病的相关术语**：
            - 核心概念：癫痫
              → 相关术语：neuronal hyperexcitability（神经元过度兴奋）, convulsion（抽搐）, status epilepticus（癫痫持续状态）, temporal lobe（颞叶）, hippocampus（海马）等等
            - 核心概念：皮肌炎
              → 相关术语：muscle inflammation（肌肉炎症）, skin rash（皮疹）, muscle weakness（肌无力）, heliotrope rash（向阳疹）, interstitial lung disease（间质性肺病）等等

            **药物/治疗的相关术语**：
            - 核心概念：免疫抑制剂
              → 相关术语：T cell inhibition（T细胞抑制）, B cell depletion（B细胞耗竭）, immune modulation（免疫调节）, inflammation control（炎症控制）等等
            - 核心概念：IVIG
              → 相关术语：immunoglobulin therapy（免疫球蛋白治疗）, passive immunization（被动免疫）, antibody replacement（抗体替代）等等

            **操作指南**：
            - 不限于上述例子，请举一反三
            - 如果发现缺少具体实例，优先补充5-10个常见实例
            - 添加核心概念的相关术语和机制词汇
            - 添加相关的病理生理术语、解剖结构术语、临床表现术语
            - 保持与用户查询"{user_query}"的直接相关性
            - 每轮适度增加2-3个相关术语
            - 所有术语用OR连接
            - 保持检索式结构清晰
            """
        elif attempt_number <= stage3_end:
            # 📊 第三阶段：诊断-调整策略（默认21-30轮，占总轮次的40%-60%）
            if current_results_count < low_threshold:  # 默认<50篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 诊断与调整（关键阶段！）**

                **当前状态**: 第{attempt_number}轮（第三阶段：{stage2_end+1}-{stage3_end}轮），已有{current_results_count}篇文献（少于{low_threshold}篇）
                **策略**: 先诊断问题，再针对性调整

                ---

                **第一步：自我诊断（必须先诊断！）**

                请仔细检查当前检索式"{failed_query}"，回答以下诊断问题：

                **诊断1 - 布尔逻辑检查**：
                - ❓ 我是否错误地将**并列的概念**用AND连接了？比如：
                - 示例错误：(service delivery) AND (behavioral intervention) AND (self-management)
                - 正确做法：(service delivery OR behavioral intervention OR self-management)
                - 检查要点：
                  * 如果用户查询中有"A、B和C"或"A, B, and C"，这些应该用OR连接
                  * 如果用户查询中有"A对B的影响"，只有A和B是不同维度，才用AND

                **诊断2 - 实例扩展检查，比如**：
                - ❓ 我的干预/治疗/诊断概念是否是一个**抽象的类别**？
                - ❓ 如果是类别，我是否已经包含了**足够多的具体实例**（至少5-10个）？
                - 检查要点，比如：
                  * "靶向治疗" → 是否包含rituximab, abatacept, tocilizumab等具体药物？
                  * "行为干预" → 是否包含CBT, relaxation, meditation等具体方法？
                  * "服务提供" → 是否包含pharmaceutical care, nurse specialist等具体模式？
                  * "焦虑筛查" → 是否包含HADS, GAD-7, BAI等具体工具？

                **诊断3 - 概念理解检查，比如**：
                - ❓ 我对用户查询"{user_query}"中的核心概念（尤其是缩写）的理解是否准确？
                - ❓ 是否存在其他可能的专业含义？

                ---

                **第二步：基于诊断进行调整**

                **如果诊断1有问题**（布尔逻辑错误）：
                - 则修正布尔逻辑
                - 比如将错误的AND改为OR（需明确错误的情况下才修改）
                - 示例：
                  * 错误：(A) AND (B) AND (C)
                  * 正确：(A OR B OR C)
                  * 错误：(epilepsy) AND (service delivery) AND (behavioral intervention) AND (self-management)
                  * 正确：(epilepsy) AND (service delivery OR behavioral intervention OR self-management)

                **如果诊断2有问题**（缺少具体实例）：
                - **第二优先级**：进行横向实例扩展
                - 为抽象类别补充5-10个具体实例
                - 参考以下示例，比如：

                **药物类别实例扩展**：
                - "靶向治疗" → 添加 "rituximab"[tiab] OR "abatacept"[tiab] OR "tocilizumab"[tiab] OR "belimumab"[tiab] OR "infliximab"[tiab]
                - "免疫抑制剂" → 添加 "methotrexate"[tiab] OR "azathioprine"[tiab] OR "cyclosporine"[tiab] OR "mycophenolate"[tiab]
                - "IVIG" → 添加 "intravenous immune globulin"[tiab] OR "intravenous immunoglobulin"[tiab] OR "IVIg"[tiab]

                **干预类别实例扩展**：
                - "行为干预" → 添加 "cognitive behavioral therapy"[tiab] OR "CBT"[tiab] OR "relaxation"[tiab] OR "meditation"[tiab] OR "mindfulness"[tiab] OR "biofeedback"[tiab]
                - "服务提供" → 添加 "pharmaceutical care"[tiab] OR "nurse specialist"[tiab] OR "epilepsy nurse"[tiab] OR "nurse-led clinic"[tiab] OR "home-based care"[tiab] OR "telemedicine"[tiab]
                - "自我管理" → 添加 "patient education"[tiab] OR "self-monitoring"[tiab] OR "medication adherence"[tiab] OR "lifestyle modification"[tiab]

                **诊断工具实例扩展**：
                - "焦虑筛查" → 添加 "HADS"[tiab] OR "HADS-A"[tiab] OR "GAD-7"[tiab] OR "Beck Anxiety Inventory"[tiab] OR "BAI"[tiab]
                - "抑郁筛查" → 添加 "PHQ-9"[tiab] OR "BDI"[tiab] OR "HADS-D"[tiab] OR "Hamilton Depression Rating Scale"[tiab]

                **细胞类型实例扩展**：
                - "胶质细胞" → 添加 "astrocyte"[mesh] OR "GFAP"[tiab] OR "microglia"[mesh] OR "Iba1"[tiab] OR "oligodendrocyte"[mesh]
                - "免疫细胞" → 添加 "T cells"[mesh] OR "B cells"[mesh] OR "macrophages"[mesh] OR "dendritic cells"[mesh] OR "NK cells"[mesh]

                **如果诊断3有问题**（概念理解错误）：
                - **最高优先级**：重新理解核心概念
                - 重新生成检索式

                **如果以上诊断都没有问题**：
                - 则进行以下**适度向上扩展**（寻找更宽泛的术语）
                - 参考以下向上扩展示例，比如：

                **向上扩展多领域示例（请举一反三）**：

                **生物基础研究领域：**
                1. 星型胶质细胞 → 胶质细胞 → 神经胶质 → 脊髓微环境
                2. T细胞 → 免疫细胞 → 炎症细胞 → 免疫反应
                3. 线粒体功能障碍 → 细胞器功能 → 细胞代谢 → 能量代谢

                **分子生物学领域：**
                4. CRISPR-Cas9 → 基因编辑技术 → 分子生物学技术 → 生物技术
                5. mRNA疫苗 → 核酸疫苗 → 疫苗技术 → 免疫预防

                **临床医学领域：**
                6. 冠状动脉支架 → 血管介入器械 → 心血管介入 → 介入治疗
                7. 阿尔茨海默病 → 神经退行性疾病 → 认知障碍 → 神经系统疾病

                **医工结合领域：**
                8. 脑机接口 → 神经工程 → 生物医学工程 → 医疗器械
                9. 3D生物打印 → 组织工程 → 再生医学 → 生物制造

                **药物研发领域：**
                10. PD-1抑制剂 → 免疫检查点抑制剂 → 免疫治疗 → 肿瘤治疗

                **向上扩展原则：**
                - 从具体分子/细胞 → 细胞类型/通路 → 生物学过程 → 疾病机制
                - 从特定技术 → 技术类别 → 研究方法 → 学科领域
                - 从单一靶点 → 信号通路 → 生理系统 → 病理过程

                ---

                **调整优先级总结**：
                1. 布尔逻辑错误 → 立即修正（最高优先级）
                2. 缺少具体实例 → 横向实例扩展（第二优先级）
                3. 概念理解错误 → 重新生成（最高优先级）
                4. 以上都没问题 → 适度向上扩展
                5. 不限于上述例子，请举一反三
                """
            elif low_threshold <= current_results_count <= mid_threshold2:  # 默认50-200篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 相关术语深化扩展**

                **当前状态**: 第{attempt_number}轮（第三阶段：{stage2_end+1}-{stage3_end}轮），已有{current_results_count}篇文献（{low_threshold}-{mid_threshold2}篇）
                **扩展策略**: 文献数适中，继续添加相关术语，深化检索范围

                **相关术语扩展的具体操作**：

                **第一步：识别可扩展的维度**

                检查当前检索式"{failed_query}"，识别可扩展的维度，比如以下（请举一反三）：

                1. **病理生理维度**：
                   - 如果查询涉及疾病，添加相关的病理生理过程
                   - 示例：
                     * "癫痫" → 添加 "seizure disorder"[tiab] OR "epileptic syndrome"[tiab] OR "convulsions"[mesh]
                     * "皮肌炎" → 添加 "inflammatory myopathy"[tiab] OR "muscle inflammation"[tiab] OR "myositis"[mesh]

                2. **分子机制维度**：
                   - 如果查询涉及治疗/干预，添加相关的作用机制
                   - 示例：
                     * "免疫抑制剂" → 添加 "immunomodulation"[tiab] OR "immune regulation"[tiab] OR "T cell suppression"[tiab]
                     * "靶向治疗" → 添加 "B cell depletion"[tiab] OR "cytokine inhibition"[tiab] OR "receptor blockade"[tiab]

                3. **细胞/组织维度**：
                   - 如果查询涉及基础研究，添加相关的细胞类型或组织结构
                   - 示例：
                     * "脊髓损伤" → 添加 "spinal cord tissue"[tiab] OR "neural tissue"[tiab] OR "gray matter"[tiab] OR "white matter"[tiab]
                     * "肿瘤微环境" → 添加 "tumor stroma"[tiab] OR "extracellular matrix"[tiab] OR "tumor vasculature"[tiab]

                4. **临床表现维度**：
                   - 如果查询涉及疾病，添加相关的临床症状或体征
                   - 示例：
                     * "癫痫" → 添加 "seizure frequency"[tiab] OR "seizure control"[tiab] OR "epileptic activity"[tiab]
                     * "焦虑" → 添加 "anxiety symptoms"[tiab] OR "worry"[tiab] OR "nervousness"[tiab] OR "panic"[tiab]

                5. **治疗结局维度**：
                   - 如果查询涉及治疗效果，添加相关的结局指标
                   - 示例：
                     * "疗效" → 添加 "treatment response"[tiab] OR "clinical improvement"[tiab] OR "remission"[tiab] OR "disease activity"[tiab]
                     * "生活质量" → 添加 "functional status"[tiab] OR "disability"[tiab] OR "daily activities"[tiab] OR "well-being"[tiab]

                **第二步：选择优先扩展的维度**

                根据用户查询"{user_query}"的核心关注点，优先扩展最相关的1-2个维度：
                - 如果查询强调"机制"，优先扩展分子机制维度
                - 如果查询强调"疗效"，优先扩展治疗结局维度
                - 如果查询强调"诊断"，优先扩展临床表现维度

                **第三步：适度添加术语**

                - 每轮添加2-3个相关术语即可，不要过度扩展
                - 所有新术语用OR连接到对应的概念组
                - 保持检索式的可读性和结构清晰

                **扩展原则**：
                - ✅ 添加与核心概念直接相关的术语
                - ✅ 优先添加MeSH术语和标准医学术语
                - ✅ 保持与用户查询"{user_query}"的直接相关性
                - ❌ 避免跨领域的概念扩展
                - ❌ 避免添加过于宽泛的术语
                """

            else:  # >mid_threshold2，默认>200篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 保守同义词扩展**

                **当前状态**: 第{attempt_number}轮（第三阶段：{stage2_end+1}-{stage3_end}轮），已有{current_results_count}篇文献（超过{mid_threshold2}篇）
                **扩展策略**: 文献数已较多，保守扩展，避免过度稀释

                **保守扩展的具体操作**：

                **第一步：识别核心概念的遗漏同义词**

                检查当前检索式"{failed_query}"，识别是否有核心概念的重要同义词被遗漏（请举一反三）：

                **疾病/病症的同义词**：
                - 检查是否包含疾病的所有常用名称
                - 示例：
                  * "癫痫" → 是否包含 "epilepsy"[mesh] AND "seizures"[mesh] AND "epilepsy"[tiab]？
                  * "皮肌炎" → 是否包含 "dermatomyositis"[mesh] AND "dermatomyositis"[tiab]？
                  * "阿尔茨海默病" → 是否包含 "Alzheimer disease"[mesh] AND "Alzheimer's disease"[tiab] AND "AD"[tiab]？

                **药物/治疗的同义词**：
                - 检查是否包含药物的通用名、商品名、缩写
                - 示例：
                  * "IVIG" → 是否包含 "intravenous immune globulin"[tiab] AND "intravenous immunoglobulin"[tiab] AND "IVIg"[tiab]？
                  * "阿司匹林" → 是否包含 "aspirin"[mesh] AND "acetylsalicylic acid"[tiab] AND "ASA"[tiab]？

                **诊断工具的同义词**：
                - 检查是否包含工具的全称、缩写、不同版本
                - 示例：
                  * "HADS" → 是否包含 "Hospital Anxiety and Depression Scale"[tiab] AND "HADS"[tiab]？
                  * "MRI" → 是否包含 "magnetic resonance imaging"[tiab] AND "MRI"[tiab] AND "MR imaging"[tiab]？

                **第二步：仅添加最核心的遗漏同义词**

                - **严格标准**：只添加那些"如果不加就会漏掉重要文献"的同义词
                - **数量限制**：每轮最多添加1-2个同义词
                - **优先级**：
                  1. 优先添加MeSH术语（如果尚未包含）
                  2. 其次添加标准缩写（如"AD"代表"Alzheimer's disease"）
                  3. 最后添加常用的拼写变体（如"tumor"和"tumour"）

                **第三步：优化现有术语的组合方式**

                如果没有遗漏的核心同义词，考虑优化检索式的结构：

                **优化方法1：调整字段标签**
                - 检查是否有术语只用了[tiab]，可以补充[mesh]
                - 示例：
                  * 当前：("epilepsy"[tiab])
                  * 优化：("epilepsy"[mesh] OR "epilepsy"[tiab])

                **优化方法2：调整括号嵌套**
                - 检查括号嵌套是否清晰，是否可以简化
                - 确保每个概念组都有明确的括号包裹

                **优化方法3：移除冗余术语**
                - 检查是否有完全重复或高度重叠的术语
                - 示例：如果已有"epilepsy"[mesh]，可能不需要"epileptic disorder"[tiab]

                **保守扩展原则**：
                - ✅ 仅添加核心概念的直接同义词
                - ✅ 优先添加MeSH术语和标准缩写
                - ✅ 保持检索的精确性，避免语义漂移
                - ✅ 优化现有术语的字段标签和组合方式
                - ❌ 绝对不要添加宽泛的上位概念
                - ❌ 绝对不要添加跨领域的术语
                - ❌ 绝对不要添加边缘相关的术语

                **质量控制**：
                - 每添加一个术语，都要问自己："如果不加这个词，会漏掉重要文献吗？"
                - 如果答案是"不会"，就不要添加
                """
        elif attempt_number <= stage4_end:
            # 📈 第四阶段：继续诊断-调整 + 深度向上扩展（默认31-40轮，占总轮次的60%-80%）
            if current_results_count < mid_threshold1:  # 默认<120篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 继续诊断 + 深度向上扩展**

                **当前状态**: 第{attempt_number}轮（第四阶段：{stage3_end+1}-{stage4_end}轮），已有{current_results_count}篇文献（少于{mid_threshold1}篇）
                **策略**: 继续诊断，并深度向上扩展

                ---

                **第一步：快速诊断检查**

                请仔细检查当前检索式"{failed_query}"，回答以下诊断问题：

                **诊断1 - 布尔逻辑检查（请举一反三）**：
                - ❓ 我是否错误地将**并列的概念**用AND连接了？比如：
                - 示例错误：(service delivery) AND (behavioral intervention) AND (self-management)
                - 正确做法：(service delivery OR behavioral intervention OR self-management)
                - 检查要点：
                  * 如果用户查询中有"A、B和C"或"A, B, and C"，这些应该用OR连接
                  * 如果用户查询中有"A对B的影响"，只有A和B是不同维度，才用AND

                **诊断2 - 实例扩展检查，比如（请举一反三）**：
                - ❓ 我的干预/治疗/诊断概念是否是一个**抽象的类别**？
                - ❓ 如果是类别，我是否已经包含了**足够多的具体实例**（至少5-10个）？
                - 检查要点，比如：
                  * "靶向治疗" → 是否包含rituximab, abatacept, tocilizumab等具体药物？
                  * "行为干预" → 是否包含CBT, relaxation, meditation等具体方法？
                  * "服务提供" → 是否包含pharmaceutical care, nurse specialist等具体模式？
                  * "焦虑筛查" → 是否包含HADS, GAD-7, BAI等具体工具？

                **诊断3 - 概念理解检查，比如（请举一反三）**：
                - ❓ 我对用户查询"{user_query}"中的核心概念（尤其是缩写）的理解是否准确？
                - ❓ 是否存在其他可能的专业含义？

                ---

                **如果发现问题，立即修正**：

                **如果诊断1有问题**（布尔逻辑错误）：
                - **最高优先级**：立即修正布尔逻辑
                - 将错误的AND改为OR
                - 示例：
                  * 错误：(epilepsy) AND (service delivery) AND (behavioral intervention) AND (self-management)
                  * 正确：(epilepsy) AND (service delivery OR behavioral intervention OR self-management)

                **如果诊断2有问题**（缺少具体实例）：
                - **第二优先级**：进行横向实例扩展
                - 为抽象类别补充5-10个具体实例
                - 参考以下示例，比如：
                  * "靶向治疗" → 添加 "rituximab"[tiab] OR "abatacept"[tiab] OR "tocilizumab"[tiab] OR "belimumab"[tiab] OR "infliximab"[tiab]
                  * "行为干预" → 添加 "cognitive behavioral therapy"[tiab] OR "CBT"[tiab] OR "relaxation"[tiab] OR "meditation"[tiab]
                  * "焦虑筛查" → 添加 "HADS"[tiab] OR "HADS-A"[tiab] OR "GAD-7"[tiab] OR "Beck Anxiety Inventory"[tiab] OR "BAI"[tiab]

                **如果诊断3有问题**（概念理解错误）：
                - **最高优先级**：重新理解核心概念
                - 重新生成检索式

                ---

                **第二步：深度向上扩展（不得因为执行了第一步修正就忽略了第二步的向上扩展策略）**

                **向上扩展多领域示例**：

                **生物基础研究领域**：
                1. 星型胶质细胞 → 胶质细胞 → 神经胶质 → 脊髓微环境 → 中枢神经系统细胞
                2. T细胞 → 免疫细胞 → 炎症细胞 → 免疫反应 → 炎症反应
                3. 线粒体功能障碍 → 细胞器功能 → 细胞代谢 → 能量代谢 → 细胞生物学

                **分子生物学领域**：
                4. CRISPR-Cas9 → 基因编辑技术 → 分子生物学技术 → 生物技术
                5. mRNA疫苗 → 核酸疫苗 → 疫苗技术 → 免疫预防

                **临床医学领域**：
                6. 冠状动脉支架 → 血管介入器械 → 心血管介入 → 介入治疗 → 微创治疗
                7. 阿尔茨海默病 → 神经退行性疾病 → 认知障碍 → 神经系统疾病 → 老年疾病

                **医工结合领域**：
                8. 脑机接口 → 神经工程 → 生物医学工程 → 医疗器械 → 康复技术
                9. 3D生物打印 → 组织工程 → 再生医学 → 生物制造 → 医疗技术

                **药物研发领域**：
                10. PD-1抑制剂 → 免疫检查点抑制剂 → 免疫治疗 → 肿瘤治疗 → 癌症治疗

                **向上扩展原则**：
                - 从具体分子/细胞 → 细胞类型/通路 → 生物学过程 → 疾病机制 → 治疗领域
                - 从特定技术 → 技术类别 → 研究方法 → 学科领域 → 医学应用
                - 从单一靶点 → 信号通路 → 生理系统 → 病理过程 → 临床表现

                **针对当前查询"{user_query}"的向上扩展指导**：
                - 每次向上一级扩展一个层级
                - 寻找更宽泛的研究背景和应用领域
                - 保持与原始查询的逻辑联系
                - 优先使用OR连接，扩大检索范围
                """
            elif mid_threshold1 <= current_results_count <= high_threshold:  # 默认120-250篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 相关术语深度扩展**

                **当前状态**: 第{attempt_number}轮（第四阶段：{stage3_end+1}-{stage4_end}轮），已有{current_results_count}篇文献（{mid_threshold1}-{high_threshold}篇）
                **扩展策略**: 文献数适中，深度扩展相关术语，拓宽检索范围

                **深度扩展的具体操作**：

                **第一步：识别可深度扩展的方向**

                检查当前检索式"{failed_query}"，识别以下可深度扩展的方向（请举一反三）：

                **方向1：研究方法和技术**
                - 如果查询涉及特定技术，添加相关的研究方法
                - 示例：
                  * "基因编辑" → 添加 "gene knockout"[tiab] OR "gene silencing"[tiab] OR "RNA interference"[tiab] OR "RNAi"[tiab]
                  * "影像诊断" → 添加 "imaging biomarker"[tiab] OR "radiomics"[tiab] OR "image analysis"[tiab]
                  * "测序" → 添加 "genomic profiling"[tiab] OR "transcriptomics"[tiab] OR "bioinformatics"[tiab]

                **方向2：临床应用和转化研究**
                - 如果查询涉及基础研究，添加临床转化相关术语
                - 示例：
                  * "细胞治疗" → 添加 "clinical trial"[tiab] OR "translational research"[tiab] OR "therapeutic application"[tiab]
                  * "生物标志物" → 添加 "diagnostic marker"[tiab] OR "prognostic marker"[tiab] OR "predictive marker"[tiab]
                  * "药物靶点" → 添加 "drug development"[tiab] OR "therapeutic target"[tiab] OR "precision medicine"[tiab]

                **方向3：相关疾病和并发症**
                - 如果查询涉及特定疾病，添加相关疾病或并发症
                - 示例：
                  * "癫痫" → 添加 "status epilepticus"[tiab] OR "refractory epilepsy"[tiab] OR "epilepsy comorbidity"[tiab]
                  * "糖尿病" → 添加 "diabetic complications"[tiab] OR "diabetic neuropathy"[tiab] OR "diabetic retinopathy"[tiab]
                  * "心血管疾病" → 添加 "cardiovascular events"[tiab] OR "cardiac dysfunction"[tiab] OR "vascular disease"[tiab]

                **方向4：相关人群和亚组**
                - 如果查询涉及特定人群，添加相关的亚组或人群特征
                - 示例：
                  * "成人" → 添加 "adult patients"[tiab] OR "young adults"[tiab] OR "middle-aged"[tiab]
                  * "儿童" → 添加 "pediatric patients"[tiab] OR "children"[mesh] OR "adolescents"[tiab]
                  * "老年人" → 添加 "elderly"[tiab] OR "aged"[mesh] OR "geriatric patients"[tiab]

                **方向5：相关结局和评估指标**
                - 如果查询涉及治疗效果，添加更多结局指标
                - 示例：
                  * "疗效" → 添加 "survival"[tiab] OR "mortality"[tiab] OR "morbidity"[tiab] OR "adverse events"[tiab]
                  * "生活质量" → 添加 "patient satisfaction"[tiab] OR "health status"[tiab] OR "symptom burden"[tiab]
                  * "功能恢复" → 添加 "functional outcome"[tiab] OR "rehabilitation"[tiab] OR "recovery"[tiab]

                **第二步：选择最相关的扩展方向**

                根据用户查询"{user_query}"的核心关注点，选择1-2个最相关的扩展方向（请举一反三）：
                - 如果查询强调"技术"，优先扩展研究方法和技术
                - 如果查询强调"临床"，优先扩展临床应用和转化研究
                - 如果查询强调"人群"，优先扩展相关人群和亚组

                **第三步：适度添加深度术语**

                - 每轮添加2-3个深度相关术语
                - 所有新术语用OR连接到对应的概念组
                - 保持与用户查询的相关性

                **深度扩展原则**：
                - ✅ 添加更深层次的相关术语
                - ✅ 添加相关的研究方法和技术
                - ✅ 添加相关的临床应用和转化研究
                - ✅ 保持与用户查询"{user_query}"的直接相关性
                - ❌ 避免添加过于宽泛的学科术语
                - ❌ 避免跨领域的概念扩展
                """

            else:  # >high_threshold，默认>250篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 保守同义词扩展**

                **当前状态**: 第{attempt_number}轮（第四阶段：{stage3_end+1}-{stage4_end}轮），已有{current_results_count}篇文献（超过{high_threshold}篇）
                **扩展策略**: 文献数已很多，保守添加核心同义词

                **第一步：识别核心概念的遗漏同义词**

                检查当前检索式"{failed_query}"中的核心概念，识别是否有遗漏的同义词，比如：

                **疾病/病症的同义词检查**：
                - 如果有"epilepsy"，是否包含所有常用表达？
                  → 检查是否缺少：seizure disorder, convulsive disorder, epileptic seizure等等
                - 如果有"dermatomyositis"，是否包含所有常用表达？
                  → 检查是否缺少：DM, juvenile dermatomyositis, JDM等等
                - 如果有"heart failure"，是否包含所有常用表达？
                  → 检查是否缺少：cardiac failure, HF, congestive heart failure, CHF等等

                **药物/治疗的同义词检查**：
                - 如果有"immunosuppressive agents"，是否包含所有常用表达？
                  → 检查是否缺少：immunosuppressants, immunosuppressive drugs, immune suppressants等等
                - 如果有"IVIG"，是否包含所有常用表达？
                  → 检查是否缺少：intravenous immunoglobulin, intravenous immune globulin, IVIg等等

                **诊断工具的同义词检查**：
                - 如果有"HADS"，是否包含全称？
                  → 检查是否缺少：Hospital Anxiety and Depression Scale等等
                - 如果有"MRI"，是否包含所有常用表达？
                  → 检查是否缺少：magnetic resonance imaging, MR imaging等等

                **第二步：仅添加最核心的遗漏同义词**

                - **严格标准**：只添加那些"如果不加就会漏掉重要文献"的同义词
                - **数量限制**：每轮最多添加1-2个同义词
                - **优先级**：
                  1. 优先添加MeSH术语（如果尚未包含）
                  2. 其次添加标准缩写（如"AD"代表"Alzheimer's disease"）
                  3. 最后添加常用的拼写变体（如"tumor"和"tumour"）

                **第三步：优化现有术语的组合方式**

                如果没有遗漏的核心同义词，考虑优化检索式的结构：

                **优化方法1：调整字段标签**
                - 检查是否有术语只用了[tiab]，可以补充[mesh]
                - 示例：
                  * 当前：("epilepsy"[tiab])
                  * 优化：("epilepsy"[mesh] OR "epilepsy"[tiab])

                **优化方法2：调整括号嵌套**
                - 检查括号嵌套是否清晰，是否可以简化
                - 确保每个概念组都有明确的括号包裹

                **优化方法3：移除冗余术语**
                - 检查是否有完全重复或高度重叠的术语
                - 示例：如果已有"epilepsy"[mesh]，可能不需要"epileptic disorder"[tiab]

                **保守扩展原则**：
                - ✅ 仅添加核心概念的直接同义词
                - ✅ 优先添加MeSH术语和标准缩写
                - ✅ 保持检索的精确性，避免语义漂移
                - ✅ 优化现有术语的字段标签和组合方式
                - ✅ 不限于上述例子，请举一反三
                - ❌ 绝对不要添加宽泛的上位概念
                - ❌ 绝对不要添加跨领域的术语
                - ❌ 绝对不要添加边缘相关的术语

                **质量控制**：
                - 每添加一个术语，都要问自己："如果不加这个词，会漏掉重要文献吗？"
                - 如果答案是"不会"，就不要添加
                - 当前文献数已经很多，质量比数量更重要
                """
        else:
            # 🚀 第五阶段：最终策略调整（默认41-50轮，占总轮次的最后20%）
            if current_results_count < very_low_threshold:  # 默认<20篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 最终手段：强制最大化向上扩展**

                **当前状态**: 第{attempt_number}轮（第五阶段：{stage4_end+1}-{max_attempts}轮），已有{current_results_count}篇文献（严重少于{very_low_threshold}篇）
                **核心策略**: 当前文献数量严重不足，当前检索策略定义过于狭窄，必须立即进行最大化向上扩展。请执行最大化向上扩展策略。这是当前轮次的重要任务。

                **🆘 核心任务：重构检索式以最大化范围 🆘**

                **行动指令：**
                1.  **分析上次检索式**: 识别上次检索中最核心、最具体的1-2个概念。
                2.  **逻辑向上扩展一级**: 将这些核心概念**替换为**逻辑上更宽泛一级的上位词。
                3.  **构建新检索式**: 基于新的、更宽泛的上位词，构建一个**全新的更广泛的**检索式。
                4.  **禁止跳跃扩展**: 向上扩展必须是逐级的。                
                5.  **移除所有 `NOT` 子句**: 这是非常重要的第一步。

                ---

                **最大化扩展示例（注意只是示例，需要请你举一反三）**：

                **领域1：生物基础研究**

                - **示例**: 将 `星型胶质细胞 (Astrocytes)` **扩展为** `中枢神经系统细胞 (Central Nervous System Cells)`
                - **示例**: 将 `中枢神经系统细胞` **扩展为** `神经系统 (Nervous System)`
                - **示例**: 将 `神经系统` **扩展为** `神经科学 (Neuroscience)`  

                - **示例**: 将 `T细胞 (T-cells)` **扩展为** `炎症反应 (Inflammatory Response)`
                - **示例**: 将 `炎症反应` **扩展为** `免疫系统 (Immune System)`
                - **示例**: 将 `免疫系统` **扩展为** `病理生理学 (Pathophysiology)` 

                - **示例**: 将 `线粒体功能障碍 (Mitochondrial Dysfunction)` **扩展为** `细胞生物学 (Cell Biology)`
                - **示例**: 将 `细胞生物学` **扩展为** `分子生物学 (Molecular Biology)`
                - **示例**: 将 `分子生物学` **扩展为** `生命科学 (Life Sciences)` 

                **领域2：临床医学**

                - **示例**: 将 `冠状动脉支架 (Corony Stents)` **扩展为** `微创治疗 (Minimally Invasive Therapy)`
                - **示例**: 将 `微创治疗` **扩展为** `心血管医学 (Cardiovascular Medicine)` 

                - **示例**: 将 `阿尔茨海默病 (Alzheimer's Disease)` **扩展为** `老年疾病 (Geriatric Diseases)`
                - **示例**: 将 `老年疾病` **扩展为** `内科学 (Internal Medicine)` 

                - **示例**: 将 `新生血管性AMD (nAMD)` **扩展为** `脉络膜新生血管 (Choroidal Neovascularization)`
                - **示例**: 将 `脉络膜新生血管` **扩展为** `眼底新生血管 (Fundus Neovascularization)`
                - **示例**: 将 `眼底新生血管` **扩展为** `新生血管（病理性） (Neovascularization, Pathologic)` 

                - **示例**: 将 `黄斑萎缩 (Macular Atrophy)` **扩展为** `视网膜变性 (Retinal Degeneration)`
                - **示例**: 将 `视网膜变性` **扩展为** `视觉障碍 (Vision Disorders)` 

                **领域3：医工结合**

                - **示例**: 将 `脑机接口 (Brain-Computer Interface)` **扩展为** `康复技术 (Rehabilitation Technology)`
                - **示例**: 将 `康复技术` **扩展为** `生物医学 (Biomedicine)` 

                - **示例**: 将 `3D生物打印 (3D Bioprinting)` **扩展为** `医疗技术 (Medical Technology)`
                - **示例**: 将 `医疗技术` **扩展为** `生物工程 (Bioengineering)`

                - **示例**: 将 `光学相干断层扫描 (OCT)` **扩展为** `视网膜成像 (Retinal Imaging)`
                - **示例**: 将 `视网膜成像` **扩展为** `诊断成像 (Diagnostic Imaging)`
                - **示例**: 将 `诊断成像` **扩展为** `成像 (Imaging)` 

                **领域4：药物研发**

                - **示例**: 将 `PD-1抑制剂 (PD-1 inhibitors)` **扩展为** `癌症治疗 (Cancer Therapy)`
                - **示例**: 将 `癌症治疗` **扩展为** `肿瘤学 (Oncology)` 

                - **示例**: 将 `阿司匹林 (Aspirin)` **扩展为** `非甾体抗炎药 (NSAIDs)`
                - **示例**: 将 `非甾体抗炎药 (NSAIDs)` **扩展为** `抗炎药 (Anti-inflammatory Agents)` 

                **强制最大化扩展原则**:
                - **对检索式中的关键检索词在原来基础上向上扩展**
                - **必须**扩展到相关的学科领域和研究方向
                - **必须**降低检索的严格程度，可以使用OR连接
                - 针对查询"{user_query}"，使用宽泛但仍相关的概念组合
                - **必须**优先使用OR连接，最大化包容性
                - 不限于上述例子，请举一反三
                """
            elif current_results_count > high_threshold:  # 默认>250篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 保守同义词扩展**

                **当前状态**: 第{attempt_number}轮（第五阶段：{stage4_end+1}-{max_attempts}轮），已有{current_results_count}篇文献（超过{high_threshold}篇）
                **扩展策略**: 文献数已很多，保守添加核心同义词

                **第一步：识别核心概念的遗漏同义词**

                检查当前检索式"{failed_query}"中的核心概念，识别是否有遗漏的同义词，比如：

                **疾病/病症的同义词检查**：
                - 如果有"epilepsy"，是否包含所有常用表达？
                  → 检查是否缺少：seizure disorder, convulsive disorder, epileptic seizure等等
                - 如果有"dermatomyositis"，是否包含所有常用表达？
                  → 检查是否缺少：DM, juvenile dermatomyositis, JDM等等
                - 如果有"heart failure"，是否包含所有常用表达？
                  → 检查是否缺少：cardiac failure, HF, congestive heart failure, CHF等等

                **药物/治疗的同义词检查**：
                - 如果有"immunosuppressive agents"，是否包含所有常用表达？
                  → 检查是否缺少：immunosuppressants, immunosuppressive drugs, immune suppressants等等
                - 如果有"IVIG"，是否包含所有常用表达？
                  → 检查是否缺少：intravenous immunoglobulin, intravenous immune globulin, IVIg等等

                **诊断工具的同义词检查**：
                - 如果有"HADS"，是否包含全称？
                  → 检查是否缺少：Hospital Anxiety and Depression Scale等等
                - 如果有"MRI"，是否包含所有常用表达？
                  → 检查是否缺少：magnetic resonance imaging, MR imaging等等

                **第二步：仅添加最核心的遗漏同义词**

                - **严格标准**：只添加那些"如果不加就会漏掉重要文献"的同义词
                - **数量限制**：每轮最多添加1-2个同义词
                - **优先级**：
                  1. 优先添加MeSH术语（如果尚未包含）
                  2. 其次添加标准缩写（如"AD"代表"Alzheimer's disease"）
                  3. 最后添加常用的拼写变体（如"tumor"和"tumour"）

                **第三步：优化现有术语的组合方式**

                如果没有遗漏的核心同义词，考虑优化检索式的结构：

                **优化方法1：调整字段标签**
                - 检查是否有术语只用了[tiab]，可以补充[mesh]
                - 示例：
                  * 当前：("epilepsy"[tiab])
                  * 优化：("epilepsy"[mesh] OR "epilepsy"[tiab])

                **优化方法2：调整括号嵌套**
                - 检查括号嵌套是否清晰，是否可以简化
                - 确保每个概念组都有明确的括号包裹

                **优化方法3：移除冗余术语**
                - 检查是否有完全重复或高度重叠的术语
                - 示例：如果已有"epilepsy"[mesh]，可能不需要"epileptic disorder"[tiab]

                **保守扩展原则**：
                - ✅ 仅添加核心概念的直接同义词
                - ✅ 优先添加MeSH术语和标准缩写
                - ✅ 保持检索的精确性，避免语义漂移
                - ✅ 优化现有术语的字段标签和组合方式
                - ✅ 不限于上述例子，请举一反三
                - ❌ 绝对不要添加宽泛的上位概念
                - ❌ 绝对不要添加跨领域的术语
                - ❌ 绝对不要添加边缘相关的术语

                **质量控制**：
                - 每添加一个术语，都要问自己："如果不加这个词，会漏掉重要文献吗？"
                - 如果答案是"不会"，就不要添加
                - 当前文献数已经很多，质量比数量更重要
                """

            else:  # very_low_threshold <= current_results_count <= high_threshold，默认20-250篇
                strategy_instruction = f"""
                **第{attempt_number}轮检索优化 - 语法结构优化**

                **当前状态**: 第{attempt_number}轮（第五阶段：{stage4_end+1}-{max_attempts}轮），已有{current_results_count}篇文献（{very_low_threshold}-{high_threshold}篇）
                **扩展策略**: 文献数适中，优化检索语法结构以提高检索效果

                **语法结构优化的具体操作**：

                **第一步：检查并优化布尔逻辑**

                检查当前检索式"{failed_query}"的布尔逻辑是否合理：

                **优化点1：AND/OR的平衡性**
                - 检查是否有过多的AND导致检索过于严格
                - 检查是否有过多的OR导致检索过于宽泛
                - 调整建议：
                  * 如果文献数偏少（接近{very_low_threshold}篇），考虑将部分AND改为OR
                  * 如果文献数偏多（接近{high_threshold}篇），考虑将部分OR改为AND

                **优化点2：括号嵌套的清晰性**
                - 检查括号嵌套是否清晰、易读
                - 确保每个概念组都有明确的括号包裹
                - 示例：
                  * 不清晰：(A OR B) AND C OR D
                  * 清晰：((A OR B) AND C) OR D 或 (A OR B) AND (C OR D)

                **优化点3：逻辑优先级**
                - 确保AND和OR的优先级符合预期
                - 使用括号明确优先级
                - 示例：
                  * 错误：A AND B OR C AND D （优先级不明确）
                  * 正确：(A AND B) OR (C AND D) 或 A AND (B OR C) AND D

                **第二步：优化检索字段组合**

                检查字段标签的使用是否合理：

                **优化策略1：MeSH + Title/Abstract组合**
                - 对于核心概念，同时使用[mesh]和[tiab]可以提高召回率
                - 示例：
                  * 当前：("epilepsy"[tiab])
                  * 优化：("epilepsy"[mesh] OR "epilepsy"[tiab])

                **优化策略2：根据文献数调整字段精确度**
                - 如果文献数偏少，使用更宽泛的字段：
                  * [tiab]（标题+摘要）比[title]（仅标题）更宽泛
                  * [mesh]（所有MeSH词）比[majr]（主要主题词）更宽泛
                - 如果文献数偏多，使用更精确的字段：
                  * [title]比[tiab]更精确
                  * [majr]比[mesh]更精确

                **优化策略3：字段标签的一致性**
                - 检查同类概念是否使用了一致的字段标签
                - 示例：
                  * 不一致：("epilepsy"[mesh]) AND ("treatment"[tiab])
                  * 一致：("epilepsy"[mesh] OR "epilepsy"[tiab]) AND ("treatment"[mesh] OR "treatment"[tiab])

                **第三步：简化过于复杂的检索式**

                如果检索式过于复杂（长度>1000字符或概念组>5个）：

                **简化方法1：合并高度相关的术语**
                - 检查是否有可以合并的同义词
                - 示例：
                  * 复杂：("treatment"[tiab] OR "therapy"[tiab] OR "therapeutic"[tiab] OR "therapeutics"[tiab])
                  * 简化：("treatment"[tiab] OR "therapy"[tiab])

                **简化方法2：移除边缘术语**
                - 检查是否有贡献度很低的边缘术语
                - 移除那些"加了也不会增加多少文献"的术语

                **简化方法3：重组概念组**
                - 检查是否可以将多个小概念组合并为一个大概念组
                - 示例：
                  * 复杂：(A OR B) AND (C OR D) AND (E OR F) AND (G OR H)
                  * 简化：(A OR B) AND (C OR D OR E OR F) AND (G OR H)

                **第四步：优化现有术语的检索效果**

                **优化方法1：使用截词符***
                - 检查是否可以使用截词符简化检索式
                - 示例：
                  * 当前：("treatment"[tiab] OR "treatments"[tiab] OR "treating"[tiab])
                  * 优化：("treat*"[tiab])
                - 注意：截词符会增加召回率但可能降低精确度，谨慎使用

                **优化方法2：使用短语检索**
                - 对于多词短语，使用双引号确保精确匹配
                - 示例：
                  * 当前：(cognitive AND behavioral AND therapy)
                  * 优化：("cognitive behavioral therapy"[tiab])

                **优化方法3：调整术语顺序**
                - 将最核心的概念放在检索式前面
                - 将限定条件放在后面
                - 这样可以提高检索效率（虽然不影响结果）

                **语法优化原则**：
                - ✅ 调整AND/OR的组合方式，平衡精确性和召回率
                - ✅ 优化检索字段的组合([tiab], [mesh], [title]等)
                - ✅ 调整括号的嵌套结构，确保逻辑清晰
                - ✅ 简化过于复杂的检索式，提高可读性
                - ✅ 优化现有术语的检索效果（截词符、短语检索等）
                - ✅ 保持与用户查询"{user_query}"的相关性

                **质量控制**：
                - 优化后的检索式应该更清晰、更易读、更高效
                - 优化不应该改变检索的核心逻辑和范围
                """

        return f"""
        你是一位Pubmed文献检索式优化专家，请基于以下内容进行检索式优化。
        **避免在开头出现"```pubmed"诸如此类的废话！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！直接给我我可以直接复制到pubmed检索框上进行检索的检索式就好而无需其他任何废话！！**

        {strategy_instruction}

        通用要求：
        - 生成的检索式必须与上次的检索式不同
        - 每个检索单元必须使用括号包裹
        - 严禁包含任何期刊评价指标（IF、JCR、中科院分区等）
        - **严禁添加任何时间限制**（如 `[dp]`、`[pdat]`、`2021:2024[dp]` 等）。
        - 生成的检索式必须为英文
        - 使用标准的PubMed字段标签

        **PubMed标准字段标签（只能使用以下字段）：**
        - [Title/Abstract] 或 [tiab] - 标题和摘要
        - [MeSH Terms] 或 [mesh] - 医学主题词
        - [Title] 或 [ti] - 仅标题
        - [Abstract] 或 [ab] - 仅摘要
        - [Author] 或 [au] - 作者
        - [Journal] 或 [ta] - 期刊名
        - [Publication Type] 或 [pt] - 发表类型
        - [All Fields] 或 [all] - 所有字段
        - [Substance Name] - 物质名称
        - [Text Word] 或 [tw] - 文本词

        **严禁使用的错误字段标签：**
        - [Supplementary Concept] ❌
        - [Chemical] ❌
        - [Keyword] ❌
        - 任何其他非标准字段标签 ❌

        **只输出新的检索式，不需要其他任何文字说明**
        **优化后的新检索式必须与上次的检索式不同！！必须优化，而不是直接用上一轮的检索式！！**

        用户查询: "{user_query}"
        上次检索式: "{failed_query}"
        上次检索结果数量: {previous_count}篇

        直接输出新检索式：
        """

    @staticmethod
    def get_generate_scoring_criteria_prompt(user_query: str, language_config: dict = None) -> str:
        # 获取语言指令
        language_instruction = ""
        if language_config:
            language_instruction = f"\n\n# 🌍 输出语言要求\n{language_config['ai_instruction']}\n"

        return f"""{language_instruction}
# 角色
你是一位经验丰富的系统综述研究员，擅长精准地把握一个研究领域的核心问题。你的任务不是套用任何框架（如PICO），而是为一项研究的自然语言查询，设计一个直观、灵活且一致的文献筛选评分标准。

# 背景
我正在开发一个AI文献筛选系统。关键是要确保筛选标准完全忠实于用户的原始、自然的查询意图，避免任何形式的模板化。我需要你为我生成这个标准，它将成为后续自动化筛选的唯一依据。

# 任务
你的核心任务是为`{user_query}`生成评分标准。为了让你完全理解我的要求，请首先仔细学习以下12个高质量的`[示例]`，这些示例覆盖了临床研究、基础实验、医工交叉、流行病学等多个研究领域。请模仿这些示例的分析思路、结构和详细程度，然后完成最后的任务。

---
## [高质量示例]

### 示例1: 关联性研究
#### 用户查询:
`茶与抑郁症的相关性`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣在于探索"饮茶"这一日常行为与"抑郁症"这一精神健康状况之间是否存在直接的联系。兴趣点非常集中，主要关注直接研究这两者关系的人群研究，无论是探索相关性、因果性还是风险因素。任何偏离"饮茶"本身（如研究茶叶提取物）或"抑郁症"本身（如研究广泛的"情绪问题"）的文献，其相关性都会降低。

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心主题就是研究饮茶行为与抑郁症（或明确的抑郁症状诊断/量表评估）之间的关系。研究提供了关于这种关系的直接、一手数据分析。
*   **2分 (中度相关):** 摘要明确探讨了茶与抑郁症的关系，但这是其多个研究目标之一（例如，同时研究咖啡和茶）。或者，研究的核心是"饮食模式与抑郁症"，但其中对"茶"作为一个独立因素进行了详细分析。
*   **1分 (轻度相关):** 摘要的研究主题与核心兴趣存在一个层级的间接性。例如：研究茶的特定化学成分（如茶氨酸）对抑郁症的影响；或研究饮茶对与抑郁症相关的生物标志物的影响。
*   **0分 (边缘相关):** 摘要的主题并非直接研究此关系，但在背景或讨论部分提及了这种潜在联系。或为广义综述，将饮茶作为众多生活方式因素之一简单列举。
*   **-1分 (完全不相关):** 摘要完全不涉及饮茶或抑郁症中的任何一个，或者虽然提及但与查询的核心关系完全无关。

---

### 示例2: 干预措施对比研究
#### 用户查询:
`比较SGLT2抑制剂与GLP-1受体激动剂对2型糖尿病患者心血管结局的影响`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是**直接比较 (head-to-head comparison)** SGLT2抑制剂和GLP-1受体激动剂这两类药物，在特定人群（2型糖尿病患者）中，对特定结果（心血管事件）的影响。关键点在于"比较"。只研究其中一种药物而不与另一种进行比较的文献，虽然相关，但并不完全符合查询的核心意图。

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要明确描述了一项直接比较SGLT2i和GLP-1 RA对2型糖尿病患者心血管结局的临床试验（如RCT）或真实的、高质量的观察性研究。
*   **2分 (中度相关):** 摘要是一篇系统综述或Meta分析，其核心内容就是汇集和比较SGLT2i和GLP-1 RA对心血管结局的研究。或者，研究了其中一类药物，但在摘要的背景、方法或结论中与另一类药物进行了明确的、有数据支持的比较分析。
*   **1分 (轻度相关):** 摘要只研究了SGLT2i或GLP-1 RA其中一类药物对2型糖尿病患者心血管结局的影响，但完全没有提及或比较另一类药物。
*   **0分 (边缘相关):** 摘要是关于2型糖尿病心血管风险管理的广泛综述，其中将SGLT2i和GLP-1 RA作为治疗选项简单提及。
*   **-1分 (完全不相关):** 摘要完全不涉及SGLT2i、GLP-1 RA、2型糖尿病或心血管结局中的任何核心要素，或者虽然提及但与查询的核心比较完全无关。

---

### 示例3: 诊断/技术应用研究
#### 用户查询:
`液体活检在早期肺癌筛查中的应用和效果`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估"液体活检"这项技术，在特定场景（早期筛查）和特定疾病（肺癌）中的**有效性或应用价值**。重点是"早期筛查"，这意味着研究其诊断准确性（敏感性、特异性）、预测价值等。将其用于晚期癌症的治疗监测或预后判断的文献，则偏离了核心兴趣。

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估液体活检作为一种工具，用于**筛查**或**早期诊断**无症状或高危人群中的肺癌。明确报告了其筛查效果的指标（如检出率、敏感性等）。
*   **2分 (中度相关):** 摘要研究了液体活检在肺癌诊断中的应用，但可能没有严格限定在"早期"或"筛查"阶段，例如，用于辅助已出现症状患者的诊断。
*   **1分 (轻度相关):** 摘要研究了液体活检在**已确诊**的肺癌患者中的应用，例如用于监测治疗反应、检测耐药突变或判断预后。这偏离了"筛查"的核心。
*   **0分 (边缘相关):** 摘要是关于液体活检技术的综述，其中提到了在肺癌中的应用潜力。或是关于肺癌筛查的综述，其中简单提及了液体活检作为一种新兴技术。
*   **-1分 (完全不相关):** 摘要完全不涉及液体活检、肺癌或筛查中的任何核心要素，或者虽然提及但与查询的核心应用完全无关。

---

### 示例4: 诊断准确性研究
#### 用户查询:
`评估HADS-A在成人焦虑障碍筛查中的诊断准确性`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估HADS-A这一筛查工具在特定人群（成人）和特定疾病（焦虑障碍）中的诊断准确性。关键点在于"诊断准确性"，这意味着研究需要将HADS-A与金标准（如SCID、MINI）进行比较，并报告敏感性、特异性等指标。**重要的是，比较研究是评估诊断准确性的核心方法。如果一篇研究同时比较了HADS-A和其他工具（如GAD-7、BAI），这恰恰是高质量证据，不应因为"不纯粹"而降级。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估HADS-A在成人焦虑障碍筛查中的诊断准确性，与金标准（如SCID、MINI）进行比较，并报告了敏感性、特异性等指标。**即使同时比较了其他筛查工具（如GAD-7、BAI），仍然是3分，因为比较研究是评估价值的核心。**
*   **2分 (中度相关):** 摘要研究了HADS-A在焦虑障碍筛查中的应用，但可能没有严格的金标准比较，或者是在特定亚组（如癌症患者、老年人）中的应用。
*   **1分 (轻度相关):** 摘要研究了HADS-A在其他精神障碍（如抑郁症）中的应用，或者研究了HADS-A的其他心理测量学特性（如信度、效度、因子结构）。
*   **0分 (边缘相关):** 摘要是关于焦虑障碍筛查的综述，其中提到了HADS-A作为一种工具。
*   **-1分 (完全不相关):** 完全不涉及HADS-A、焦虑障碍或诊断准确性。

---

### 示例5: 单一干预措施研究-概念家族
#### 用户查询:
`评估利尿剂预防或治疗急性肾损伤的效果`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估"利尿剂"这一大类药物在预防或治疗急性肾损伤（AKI）中的效果。**关键点在于理解"利尿剂"是一个概念家族，包括袢利尿剂（如呋塞米、托拉塞米、布美他尼）、噻嗪类利尿剂、保钾利尿剂（如螺内酯、依普利酮）、渗透性利尿剂（如甘露醇）等。研究任何一种具体的利尿剂都应该被认为是高度相关的，不要因为摘要中没有明确提到"利尿剂"这个词就降级。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估利尿剂（**包括呋塞米、托拉塞米、布美他尼、甘露醇、螺内酯、依普利酮等任何一种利尿剂**）在预防或治疗AKI中的效果，研究设计为RCT或高质量观察性研究。
*   **2分 (中度相关):** 摘要研究了利尿剂在AKI患者中的应用，但主要关注其他结局（如液体平衡、尿量、电解质），AKI是次要结局。
*   **1分 (轻度相关):** 摘要研究了利尿剂在其他肾脏疾病（如慢性肾病、肾病综合征）中的应用，但不是AKI。
*   **0分 (边缘相关):** 摘要是关于AKI治疗的综述，其中提到了利尿剂作为一种治疗选项。
*   **-1分 (完全不相关):** 完全不涉及利尿剂或AKI。

---

### 示例6: 围手术期干预措施研究
#### 用户查询:
`比较不同围手术期干预措施在盆腔器官脱垂手术中的安全性和有效性`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是比较不同的"围手术期干预措施"在特定手术（盆腔器官脱垂手术）中的安全性和有效性。**关键点在于理解"围手术期干预措施"是一个广泛的概念家族，包括术前准备（如盆底肌训练、肠道准备、营养支持）、术中管理（如局部麻醉 vs 全身麻醉、导尿管管理策略）、术后护理（如抗生素预防、激素治疗如DHEA/雌激素、疼痛管理）等。研究任何一种具体的围手术期干预措施都应该被认为是高度相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是比较不同的围手术期干预措施（**如术前盆底肌训练 vs 常规护理、DHEA vs 雌激素 vs 抗生素、不同导尿管管理策略、局部麻醉 vs 全身麻醉、不同肠道准备方案等**）在POP手术中的安全性和有效性，研究设计为RCT。
*   **2分 (中度相关):** 摘要研究了某一种围手术期干预措施在POP手术中的应用，但没有与其他干预措施进行比较（如单臂研究）。
*   **1分 (轻度相关):** 摘要研究了POP手术的其他方面（如手术技术、网片材料选择、手术入路），但不是围手术期干预措施。
*   **0分 (边缘相关):** 摘要是关于POP手术的综述，其中提到了围手术期干预措施。
*   **-1分 (完全不相关):** 完全不涉及POP手术或围手术期干预措施。

---

### 示例7: 预防性干预研究-次要结局
#### 用户查询:
`评估产前或婴幼儿补充维生素D预防儿童哮喘的效果`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估维生素D补充在预防儿童哮喘中的效果。**关键点在于明确定义主要结局和次要结局。主要结局是"哮喘"（包括哮喘诊断、哮喘发病率、持续性喘息）。次要结局包括与哮喘密切相关的呼吸系统疾病（如呼吸道感染、喘息发作、特应性皮炎）。其他相关结局包括维生素D补充的其他健康效应（如骨骼健康、生长发育、免疫功能）。必须明确告诉筛选AI：研究次要结局的文献是2分，不是0分。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估产前或婴幼儿补充维生素D对儿童哮喘（包括哮喘诊断、哮喘发病率、持续性喘息）的预防效果，研究设计为RCT。
*   **2分 (中度相关):** 摘要研究了产前或婴幼儿补充维生素D对次要结局（**呼吸道感染、喘息发作、特应性皮炎**）的影响，研究设计为RCT。**即使摘要的主要结论是关于呼吸道感染而不是哮喘，仍然是2分，因为这些是与哮喘密切相关的次要结局。**
*   **1分 (轻度相关):** 摘要研究了产前或婴幼儿补充维生素D对其他健康结局（如骨骼健康、生长发育、免疫功能、过敏性鼻炎）的影响，研究设计为RCT。
*   **0分 (边缘相关):** 摘要是关于维生素D补充或儿童哮喘预防的综述。
*   **-1分 (完全不相关):** 完全不涉及维生素D补充或儿童哮喘。

---

### 示例8: 治疗效果研究-亚组分析
#### 用户查询:
`评估免疫抑制剂治疗系统性红斑狼疮的效果`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估"免疫抑制剂"这一大类药物在治疗系统性红斑狼疮（SLE）中的效果。**关键点在于理解"免疫抑制剂"是一个概念家族，包括甲氨蝶呤、硫唑嘌呤、环孢素、麦考酚酯、他克莫司、环磷酰胺等。同时，SLE是一个系统性疾病，研究特定器官受累（如狼疮肾炎、神经精神狼疮、血液系统受累）的亚组也应该被认为是高度相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估免疫抑制剂（**包括甲氨蝶呤、硫唑嘌呤、环孢素、麦考酚酯、他克莫司、环磷酰胺等任何一种**）在治疗SLE（**包括全身性SLE或特定器官受累如狼疮肾炎、神经精神狼疮**）中的效果，研究设计为RCT或高质量观察性研究。
*   **2分 (中度相关):** 摘要研究了免疫抑制剂在SLE患者中的应用，但主要关注其他结局（如生活质量、疾病活动度、生物标志物），治疗效果是次要结局。
*   **1分 (轻度相关):** 摘要研究了免疫抑制剂在其他自身免疫性疾病（如类风湿关节炎、干燥综合征）中的应用，但不是SLE。
*   **0分 (边缘相关):** 摘要是关于SLE治疗的综述，其中提到了免疫抑制剂作为一种治疗选项。
*   **-1分 (完全不相关):** 完全不涉及免疫抑制剂或SLE。

---

### 示例9: 生物基础实验研究
#### 用户查询:
`探索NLRP3炎症小体在阿尔茨海默病发病机制中的作用`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是探索NLRP3炎症小体这一分子机制在阿尔茨海默病（AD）发病中的作用。**关键点在于理解基础实验研究的多样性：包括细胞实验（如神经元、小胶质细胞、星形胶质细胞）、动物模型（如APP/PS1小鼠、5xFAD小鼠、3xTg-AD小鼠）、分子机制研究（如信号通路、蛋白相互作用、基因表达）。研究NLRP3炎症小体的任何组分（如NLRP3、ASC、Caspase-1）或下游效应（如IL-1β、IL-18、焦亡）在AD中的作用，都应该被认为是高度相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是研究NLRP3炎症小体（**包括NLRP3、ASC、Caspase-1或其下游效应分子IL-1β、IL-18、焦亡**）在AD发病机制中的作用，使用了细胞实验、动物模型或分子机制研究。
*   **2分 (中度相关):** 摘要研究了NLRP3炎症小体在其他神经退行性疾病（如帕金森病、亨廷顿病、肌萎缩侧索硬化）中的作用，或研究了AD中的其他炎症通路（如NF-κB、MAPK、JAK-STAT）但提及了NLRP3。
*   **1分 (轻度相关):** 摘要研究了NLRP3炎症小体在非神经系统疾病（如心血管疾病、代谢性疾病、自身免疫性疾病）中的作用，或研究了AD的其他发病机制（如Aβ聚集、Tau蛋白磷酸化、氧化应激）但不涉及NLRP3。
*   **0分 (边缘相关):** 摘要是关于AD发病机制或NLRP3炎症小体的综述。
*   **-1分 (完全不相关):** 完全不涉及NLRP3炎症小体或AD。

---

### 示例10: 医工交叉研究
#### 用户查询:
`评估基于深度学习的医学影像分析算法在肺结节检测中的性能`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估深度学习算法在特定临床任务（肺结节检测）中的性能。**关键点在于理解医工交叉研究的特点：既要有技术创新（如算法设计、模型训练、特征提取），也要有临床验证（如性能评估、与放射科医生比较、临床应用）。研究不同的深度学习架构（如CNN、ResNet、U-Net、Transformer、YOLO）或不同的影像模态（如CT、X光、低剂量CT）都应该被认为是相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是开发或评估基于深度学习的算法（**包括CNN、ResNet、U-Net、Transformer、YOLO等任何架构**）在肺结节检测中的性能，报告了敏感性、特异性、AUC、准确率等性能指标，或与放射科医生进行了比较。
*   **2分 (中度相关):** 摘要研究了深度学习算法在肺部其他疾病检测中的应用（如肺炎、肺癌分期、间质性肺病、肺栓塞），或研究了肺结节检测但使用传统机器学习方法（如SVM、随机森林、决策树）。
*   **1分 (轻度相关):** 摘要研究了深度学习算法在其他器官影像分析中的应用（如脑部、心脏、腹部、乳腺），或研究了肺结节的其他方面（如良恶性鉴别、生长预测、风险分层）但不是检测。
*   **0分 (边缘相关):** 摘要是关于医学影像深度学习或肺结节检测的综述。
*   **-1分 (完全不相关):** 完全不涉及深度学习、医学影像或肺结节。

---

### 示例11: 流行病学研究
#### 用户查询:
`分析空气污染与儿童哮喘发病率的关联`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是分析空气污染这一环境暴露因素与儿童哮喘发病率之间的关联。**关键点在于理解流行病学研究的多样性：包括队列研究、病例对照研究、横断面研究、生态学研究、时间序列研究。同时，"空气污染"是一个概念家族，包括PM2.5、PM10、NO2、SO2、O3、CO、交通相关空气污染（TRAP）等具体污染物。研究任何一种具体污染物与儿童哮喘的关联都应该被认为是高度相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是分析空气污染（**包括PM2.5、PM10、NO2、SO2、O3、CO、交通相关空气污染等任何一种污染物**）与儿童哮喘发病率、患病率或症状加重的关联，研究设计为队列研究、病例对照研究、横断面研究或时间序列研究。
*   **2分 (中度相关):** 摘要研究了空气污染与儿童其他呼吸系统疾病（如呼吸道感染、肺功能下降、喘息、支气管炎）的关联，或研究了空气污染与成人哮喘的关联。
*   **1分 (轻度相关):** 摘要研究了空气污染与其他健康结局（如心血管疾病、神经发育、出生结局、过敏性疾病）的关联，或研究了其他环境因素（如室内污染、过敏原、气候变化）与儿童哮喘的关联。
*   **0分 (边缘相关):** 摘要是关于空气污染健康效应或儿童哮喘流行病学的综述。
*   **-1分 (完全不相关):** 完全不涉及空气污染或儿童哮喘。

---

### 示例12: 临床研究-观察性研究
#### 用户查询:
`评估真实世界中PD-1抑制剂治疗晚期非小细胞肺癌的疗效和安全性`

#### 1. 研究查询的核心兴趣分析
该查询的核心兴趣是评估PD-1抑制剂在真实世界（而非RCT）中治疗晚期非小细胞肺癌（NSCLC）的疗效和安全性。**关键点在于理解"PD-1抑制剂"是一个概念家族，包括帕博利珠单抗（pembrolizumab）、纳武利尤单抗（nivolumab）、信迪利单抗（sintilimab）、卡瑞利珠单抗（camrelizumab）、特瑞普利单抗（toripalimab）等。同时，"真实世界研究"强调的是观察性研究设计（如回顾性队列、前瞻性队列、登记研究、数据库研究），而不是RCT。研究任何一种具体的PD-1抑制剂都应该被认为是高度相关的。**

#### 2. 文献匹配度评分标准
*   **3分 (高度相关):** 摘要的核心是评估PD-1抑制剂（**包括帕博利珠单抗、纳武利尤单抗、信迪利单抗、卡瑞利珠单抗、特瑞普利单抗等任何一种**）在真实世界中治疗晚期NSCLC的疗效（如总生存期、无进展生存期、客观缓解率）和安全性，研究设计为观察性研究（回顾性或前瞻性队列、登记研究、数据库研究）。
*   **2分 (中度相关):** 摘要研究了PD-1抑制剂治疗晚期NSCLC的疗效和安全性，但研究设计为RCT而非真实世界研究，或研究了PD-1抑制剂在早期NSCLC（如辅助治疗、新辅助治疗）或其他分期中的应用。
*   **1分 (轻度相关):** 摘要研究了PD-1抑制剂在其他癌症（如黑色素瘤、肾癌、头颈癌、胃癌、肝癌）中的应用，或研究了其他免疫检查点抑制剂（如PD-L1抑制剂、CTLA-4抑制剂）在NSCLC中的应用。
*   **0分 (边缘相关):** 摘要是关于PD-1抑制剂或NSCLC治疗的综述。
*   **-1分 (完全不相关):** 完全不涉及PD-1抑制剂或NSCLC。

---

## [关键提醒：如何设计高质量的评分标准]

基于以上12个示例，请注意以下关键要素，确保生成的评分标准详细、明确、可操作：

### 1. 理解概念的家族关系
如果用户查询涉及一个大类概念（如"利尿剂"、"免疫抑制剂"、"围手术期干预措施"、"空气污染"、"PD-1抑制剂"），评分标准应该：
- ✅ **明确列出该家族的主要成员**（如"利尿剂包括呋塞米、托拉塞米、甘露醇、螺内酯等"，请举一反三）
- ✅ **强调研究任何一种具体成员都是3分**
- ❌ 不要只说"研究利尿剂 = 3分"，要列出具体的药物/方法/污染物名称

### 2. 明确定义次要结局和相关结局
如果用户查询涉及一个主要结局，评分标准应该：
- ✅ **明确列出哪些是次要结局（2分）**
- ✅ **明确列出哪些是相关结局（1分）**
- ✅ **强调研究次要结局的文献是2分，不是0分**
- ❌ 不要让筛选AI自己推测什么是次要结局

**示例**（参考示例7）（请举一反三）：
- 用户查询："评估产前或婴幼儿补充维生素D预防儿童哮喘的效果"
- 评分标准应该明确说明：
  - 摘要中有提到主要结局（3分）：哮喘诊断、哮喘发病率、持续性喘息
  - 摘要中只提到次要结局（2分）：呼吸道感染、喘息发作、特应性皮炎
  - 摘要中只提到相关结局（1分）：骨骼健康、生长发育、免疫功能

### 3. 比较研究的灵活理解
如果用户查询涉及评估某个工具/方法的准确性或效果，评分标准应该：
- ✅ **明确说明"比较研究是评估价值的核心"**
- ✅ **强调同时比较多个工具/方法的研究仍然是3分**（如"同时比较HADS-A和GAD-7仍然是3分"）
- ❌ 不要因为"不纯粹"而降级

### 4. 研究方法和数据重于结论
评分标准应该：
- ✅ **强调关注研究的方法和数据，而不仅仅是结论**
- ✅ **如果研究报告了相关数据（如诊断准确性数据、疗效数据），即使主要结论是其他方面，仍然应该纳入**

**示例**（参考示例4）：
- 用户查询："评估分子检测方法在新生儿败血症诊断中的准确性"
- 如果一篇研究的主要结论是关于"细菌载量"或"病原体分布"，但报告了PCR vs 血培养的敏感性、特异性等诊断准确性数据，仍然应该是3分
- 因为研究方法和数据符合用户查询的核心兴趣，即使结论的侧重点不同

### 5. 人群/场景的合理扩展
评分标准应该：
- ✅ **合理扩展人群/场景的定义，不要过于狭隘**
- 示例："成人"应该包括18岁以上成人、老年人、特定人群（如癌症患者、孕妇）等
- 示例："早期筛查"应该包括无症状人群筛查、高危人群筛查等
- 示例："真实世界研究"应该包括回顾性队列、前瞻性队列、登记研究、数据库研究等

### 6. 亚组分析和特定场景的价值
如果用户查询涉及一个疾病或人群，评分标准应该：
- ✅ **认可特定亚组或特定场景的研究价值**
**示例**（参考示例8、10）：
- 用户查询："评估免疫抑制剂治疗系统性红斑狼疮的效果"
  - 研究"狼疮肾炎"（特定器官受累）也是3分
- 用户查询："评估某种药物治疗2型糖尿病的效果"
  - 研究"老年2型糖尿病患者"也是3分
- 用户查询："评估深度学习在肺结节检测中的性能"
  - 研究"深度学习在低剂量CT中的肺结节检测"也是3分

---

## [现在轮到你了！]

你已经学习了12个高质量示例，并理解了6个关键要素。现在，请严格遵循以上示例的分析方法和输出格式，并参考"关键提醒"中的6个要素，为以下用户查询生成评分标准。

**重要提醒**：
1. 如果用户查询涉及概念家族（如药物类别、干预措施类别、污染物类别），请明确列出主要成员
2. 如果用户查询涉及主要结局，请明确定义次要结局和相关结局
3. 如果用户查询涉及比较研究，请说明同时比较多个对象仍然是高分
4. 请关注研究方法和数据，而不仅仅是结论
5. 请合理扩展人群/场景的定义
6. 请认可特定亚组或特定场景的研究价值

---

## [待处理的用户查询]

### 用户查询:
`{user_query}`

### 1. 研究查询的核心兴趣分析
...

### 2. 文献匹配度评分标准
*   **3分 (高度相关):** ...
*   **2分 (中度相关):** ...
*   **1分 (轻度相关):** ...
*   **0分 (边缘相关):** ...
*   **-1分 (完全不相关):** ...

**重要提醒**: 请确保评分标准具体、可操作，能够让AI模型在后续筛选中保持一致的判断。每个评分等级的描述应该清晰区分，避免模糊地带。
"""

    @staticmethod
    def get_extract_article_info_prompt(abstract: str, user_query: str = "", scoring_criteria: str = "", current_results_count: int = 0, attempt_number: int = 1, language_config: dict = None) -> str:
        # 获取语言指令和字段显示名（用于示例说明）
        language_instruction = ""
        language_name = "English"  # 默认语言名称

        # 字段显示名（用于示例说明，从 language_config['fields'] 获取）
        field_display = {
            "score": "Relevance Score",
            "research_objective": "Research Objective",
            "study_type": "Study Type",
            "research_method": "Research Method",
            "study_population": "Study Population",
            "main_results": "Main Results",
            "conclusions": "Conclusions and Significance",
            "highlights": "Highlights and Innovations"
        }

        # 非中文语言的警告
        no_chinese_warning = ""

        if language_config:
            language_name = language_config.get('name', 'English')
            # 从 fields 获取字段显示名
            fields = language_config.get('fields', {})
            field_display = {
                "score": fields.get('score', 'Relevance Score'),
                "research_objective": fields.get('research_objective', 'Research Objective'),
                "study_type": fields.get('study_type', 'Study Type'),
                "research_method": fields.get('research_method', 'Research Method'),
                "study_population": fields.get('study_population', 'Study Population'),
                "main_results": fields.get('main_results', 'Main Results'),
                "conclusions": fields.get('conclusions', 'Conclusions and Significance'),
                "highlights": fields.get('highlights', 'Highlights and Innovations')
            }

            # 非中文语言添加警告
            if language_config.get('code', '') not in ['zh-CN', 'zh-TW', 'zh']:
                no_chinese_warning = f"""
🚫 **CRITICAL**: Since the target language is **{language_name}**, absolutely NO Chinese characters are allowed in the output! All values must be in **{language_name}** only!
"""

            language_instruction = f"""

# 🌍 Output Language Requirement
{language_config['ai_instruction']}

## Important Translation Rules
1. **JSON keys are ALWAYS in English (fixed), values are in {language_name}**
2. **Medical terminology rule**: For professional medical terms (diseases, drugs, tests, biomarkers), add English in parentheses after the translated term
   - Example (Chinese): "帕博利珠单抗 (pembrolizumab)", "非小细胞肺癌 (NSCLC)"
   - Example (Russian): "пембролизумаб (pembrolizumab)", "немелкоклеточный рак легкого (NSCLC)"
   - Example (German): "Pembrolizumab (pembrolizumab)", "nicht-kleinzelliges Lungenkarzinom (NSCLC)"
3. **Common terms don't need annotation**: Words like "patient", "treatment", "study" don't need English annotation
{no_chinese_warning}"""

        return f"""{language_instruction}
# Role
You are a professional literature screening expert who objectively and consistently evaluates the relevance of literature to research queries based on established scoring criteria.

# 🚨 Critical Screening Requirement 🚨
**IMPORTANT**: Only output JSON for scores 1-3. For scores -1 and 0, you MUST output {{}}, **especially for score 0, strictly output {{}}!!!**

# Task
Score and extract information from the given literature abstract based on the following scoring criteria.

## User Research Query
`{user_query}`

## Scoring Criteria
{scoring_criteria}

## Abstract to Evaluate
{abstract}

# Scoring Guidelines
1. **Strict adherence to criteria**: Score strictly according to the 5 levels (-1 to 3) described above
2. **Objective evaluation**: Base assessment on abstract content only, no speculation
3. **Consistency**: Similar articles should receive similar scores
4. **Conservative principle**: When in doubt, choose the lower score
5. **Strict quality threshold**: Only 1-3 score articles are included, -1 and 0 are strictly excluded
6. **Avoid misjudgment**: Do not incorrectly classify -1 or 0 score articles as 1

# Output Requirements
**If score is -1 (completely irrelevant) or 0 (marginally relevant), strictly output**: {{}}

**If score is 1-3 (substantially relevant), output the following JSON format** (Keys in English, values in {language_name}, especially study_type values in {language_name}):
{{
    "score": "[Pure number: 1/2/3]",
    "research_objective": "[Summarize research objective, annotate technical terms in English]",
    "study_type": "[Article type + study design]",
    "research_method": "[Describe research method, annotate technical terms in English]",
    "study_population": "[Population description + sample size (if available)]",
    "main_results": "[Summarize core results, annotate technical terms in English]",
    "conclusions": "[Summarize conclusions and significance]",
    "highlights": "[Extract highlights, separate multiple points with semicolons]"
}}

**Field Extraction Details**:

⚠️ **Language Consistency**: All examples below are for format reference only. Actual output must be strictly in **{language_name}**. Technical terms should be annotated with English!

1. **score** ({field_display['score']}):
   - Highly relevant: "3"
   - Moderately relevant: "2"
   - Slightly relevant: "1"
   - **IMPORTANT**: Output ONLY a pure number (1, 2, or 3), no text, parentheses, or other content!

2. **study_type** ({field_display['study_type']}):
   - **First, label the article type** (if clearly mentioned):
     * Review
     * Meta-analysis
     * RCT (Randomized Controlled Trial)
     * Cross-sectional Study
     * Case Report
     * Letter/Correspondence
     * Observational Study
   - **Then describe the specific study design**
   - Example: "Meta-analysis; systematic review of 15 RCTs"
   - Example: "Retrospective Cohort Study"
   - Example: "RCT; multicenter randomized controlled trial"

3. **study_population** ({field_display['study_population']}):
   - Describe key characteristics of the study population
   - **Must extract sample size** (if clearly stated in abstract)
   - Example: "Advanced NSCLC patients, n=245"
   - Example: "Adults aged 18-65 with T2DM, n=1,234"
   - Example (Meta-analysis): "12 studies included, total 3,456 patients"
   - If no sample size in abstract, describe population characteristics only

4. **Technical term annotation**:
   - In "research_objective", "research_method", "main_results" fields
   - Annotate professional medical terms (diseases, drugs, tests, biomarkers) with English
   - Example: "Evaluate efficacy of pembrolizumab in advanced NSCLC"

**Note**: -1 and 0 score articles output {{}}, directly excluded. **Marginally relevant and completely irrelevant abstracts strictly output {{}} only!!!**

**IMPORTANT**: Output JSON directly, no other text, start with {{ and end with }}.

⚠️ **Final language reminder**: You must use **{language_name}** for all output content. The examples above are for format reference only. If the target language is not Chinese, absolutely NO Chinese characters are allowed in the output! Technical terms should be annotated with English!

**Current screening status**: Round {attempt_number}, {current_results_count} articles screened
"""

    @staticmethod
    def get_single_field_prompt(abstract: str, field_key: str, user_query: str = "", language_config: dict = None) -> str:
        """
        生成单字段补充的 Prompt

        Args:
            abstract: 文献摘要
            field_key: 需要补充的字段键名（英文）
            user_query: 用户查询
            language_config: 语言配置

        Returns:
            单字段补充 Prompt
        """
        language_name = "English"
        field_display_name = field_key
        no_chinese_warning = ""

        # 字段描述映射（不包含 score，因为 score 为空几乎不可能）
        field_descriptions = {
            "research_objective": "Summarize the research objective/purpose of the study",
            "study_type": "Identify the article type (Review/Meta-analysis/RCT/Cohort/Case Report/etc.) and study design",
            "research_method": "Describe the research methodology used",
            "study_population": "Describe the study population/subjects and sample size (if available)",
            "main_results": "Summarize the main findings/results",
            "conclusions": "Summarize the conclusions and significance",
            "highlights": "Extract key highlights or innovations (separate with semicolons)"
        }

        if language_config:
            language_name = language_config.get('name', 'English')
            fields = language_config.get('fields', {})
            field_display_name = fields.get(field_key, field_key)

            # 非中文语言添加警告
            if language_config.get('code', '') not in ['zh-CN', 'zh-TW', 'zh']:
                no_chinese_warning = f"""
🚫 **CRITICAL**: Since target language is **{language_name}**, absolutely NO Chinese characters allowed!
"""

        field_instruction = field_descriptions.get(field_key, f"Extract information for {field_key}")

        return f"""# Task
Extract a single field from the following literature abstract.

## User Research Query
`{user_query}`

## Abstract
{abstract}

## Field to Extract
**{field_key}** ({field_display_name})

## Extraction Instruction
{field_instruction}

## Output Requirements
1. Output the field value directly, no JSON wrapping
2. Use **{language_name}** for the output
3. For professional medical terms, add English in parentheses: e.g., "pembrolizumab (pembrolizumab)"
4. Be concise but comprehensive
{no_chinese_warning}
**Output the value directly, nothing else:**
"""

# ==============================================================================
# 3. 包含通用逻辑的抽象基类
# ==============================================================================

# 🔄 重试常量（与 ArticleScreener 保持一致）
MAX_AI_RETRIES = 3
RETRY_DELAY_SECONDS = 2

class BaseClient(ABC):
    """
    所有AI客户端的抽象基类。
    它实现了所有通用的、围绕提示词构建的公共方法，
    并要求子类实现与具体API交互的 _generate_content 方法。
    """
    
    @abstractmethod
    def _generate_content(self, prompt: str, use_pro_model: bool = False, task_description: str = "AI Task", max_output_tokens: int = None) -> str:
        """
        【必须由子类实现】
        发送提示词到具体的AI API（Gemini, DeepSeek, Local）并返回结果。
        这个方法需要处理特定于其API的错误，例如速率限制。
        """
        pass

    def _generate_content_with_retry(
        self, 
        prompt: str, 
        use_pro_model: bool = False, 
        task_description: str = "AI Task", 
        max_output_tokens: int = None,
        max_retries: int = MAX_AI_RETRIES
    ) -> str:
        """
        带重试逻辑的内容生成包装器
        
        与 ArticleScreener 的重试机制保持一致：
        - 捕获所有异常
        - 最多重试 MAX_AI_RETRIES 次
        - 每次重试前等待 RETRY_DELAY_SECONDS 秒
        
        Args:
            prompt: 提示词
            use_pro_model: 是否使用 Pro 模型
            task_description: 任务描述（用于日志）
            max_output_tokens: 最大输出 Token 数
            max_retries: 最大重试次数
            
        Returns:
            AI 生成的内容
            
        Raises:
            Exception: 所有重试失败后抛出最后一个异常
        """
        import time
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = self._generate_content(
                    prompt, 
                    use_pro_model=use_pro_model, 
                    task_description=task_description, 
                    max_output_tokens=max_output_tokens
                )
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ {task_description} failed on attempt {attempt + 1}/{max_retries}: {e}. "
                        f"Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(
                        f"❌ {task_description} failed after {max_retries} attempts. Last error: {e}"
                    )
        
        # 所有重试都失败，抛出最后一个异常
        raise last_exception

    def generate_pubmed_query(self, user_query: str, attempt_number: int = 1) -> str:
        """通用方法：生成PubMed查询（带重试）"""
        prompt = ClientPrompts.get_generate_pubmed_query_prompt(user_query, attempt_number)
        task_description = f"Initial Query Generation (Attempt {attempt_number})"
        # 首轮检索式使用 pro 模型，后续轮次使用 flash 模型
        use_pro = (attempt_number == 1)
        # 增加 max_output_tokens 以避免复杂检索式被截断
        # 🔄 使用带重试的包装器
        return self._generate_content_with_retry(
            prompt, 
            use_pro_model=use_pro, 
            task_description=task_description, 
            max_output_tokens=4096
        )

    def refine_pubmed_query(self, user_query: str, failed_query: str, previous_count: int = 0, attempt_number: int = 1, current_results_count: int = 0, max_attempts: int = 50, target_articles: int = 300) -> str:
        """通用方法：优化PubMed查询（带重试）"""
        prompt = ClientPrompts.get_refine_pubmed_query_prompt(
            user_query=user_query,
            failed_query=failed_query,
            previous_count=previous_count,
            attempt_number=attempt_number,
            current_results_count=current_results_count,
            max_attempts=max_attempts,
            target_articles=target_articles
        )
        task_description = f"Refining Query (Attempt {attempt_number})"
        # 增加 max_output_tokens 以避免复杂检索式被截断
        # 🔄 使用带重试的包装器
        return self._generate_content_with_retry(
            prompt, 
            use_pro_model=False, 
            task_description=task_description, 
            max_output_tokens=4096
        )

    def generate_scoring_criteria(self, user_query: str, language_config: dict = None) -> str:
        """通用方法：生成评分标准（带重试）"""
        prompt = ClientPrompts.get_generate_scoring_criteria_prompt(user_query, language_config)
        task_description = "Scoring Criteria Generation"
        # 🔄 使用带重试的包装器
        return self._generate_content_with_retry(
            prompt, 
            use_pro_model=True, 
            task_description=task_description
        )

    def extract_article_info(self, abstract: str, user_query: str = "", scoring_criteria: str = "", current_results_count: int = 0, attempt_number: int = 1, language_config: dict = None, pmid: str = "N/A") -> str:
        """通用方法：提取文章信息"""
        prompt = ClientPrompts.get_extract_article_info_prompt(
            abstract=abstract,
            user_query=user_query,
            scoring_criteria=scoring_criteria,
            current_results_count=current_results_count,
            attempt_number=attempt_number,
            language_config=language_config
        )
        # Build a descriptive task name for logging
        task_description = f"Article Screening (PMID: {pmid})"
        return self._generate_content(prompt, use_pro_model=False, task_description=task_description)

    def fill_single_field(self, abstract: str, field_key: str, user_query: str = "", language_config: dict = None, pmid: str = "N/A") -> str:
        """
        通用方法：补充单个缺失字段

        Args:
            abstract: 文献摘要
            field_key: 需要补充的字段键名（英文，如 "research_objective"）
            user_query: 用户查询
            language_config: 语言配置
            pmid: 文献PMID

        Returns:
            AI生成的字段值
        """
        prompt = ClientPrompts.get_single_field_prompt(
            abstract=abstract,
            field_key=field_key,
            user_query=user_query,
            language_config=language_config
        )
        task_description = f"Fill Field '{field_key}' (PMID: {pmid})"
        return self._generate_content(prompt, use_pro_model=False, task_description=task_description)