// TokenSaver Pro - CLAUDE.md Configuration Generator
// Generates optimized CLAUDE.md based on user selections

// Configuration templates for each option
const CONFIG_TEMPLATES = {
  fast_mode: `### Fast Mode

Enable faster output without sacrificing quality.

**Usage:**
- Command: /fast
- Toggle on/off as needed

**Benefits:**
- Same model (Claude Opus 4.6)
- Optimized output speed
- Ideal for quick iterations`,

  parallel_exec: `### Parallel Execution

Maximize efficiency by running independent operations simultaneously.

**Rules:**
- Call independent tools in parallel, not sequentially
- Minimize API roundtrips
- Batch similar operations together

**Example:**
Instead of reading files one-by-one, read them all at once in parallel.`,

  auto_compress: `### Auto Compression

Automatic context management at memory limits.

**Behavior:**
- Activates automatically when context is full
- No manual intervention required
- Preserves critical information
- Optimizes token usage`,

  concise: `### Concise Response Style

Short, focused responses that get to the point.

**Guidelines:**
- Keep explanations brief
- Avoid unnecessary verbosity
- Use bullet points for clarity
- Skip context unless explicitly requested
- Direct answers over long narratives`,

  no_emoji: `### Professional Text Only

Maintain professional tone without emojis.

**Rules:**
- Never use emojis or emoticons
- Text-only output
- Exception: User explicitly requests emojis`,

  korean_explain: `### Language Preference

Balanced bilingual communication strategy.

**Usage:**
- Code/Commits: Always English
- Explanations: Korean preferred
- Summaries: Brief Korean before major actions
- Comments: Match project language`,

  bullet_points: `### Format Preference

Structured output using lists and points.

**Guidelines:**
- Prefer bullet points over paragraphs
- Use numbered lists for sequential steps
- Keep each point concise
- Maximum 3 levels of nesting
- Clear hierarchy`,

  smart_delegation: `### Smart Task Delegation

Optimize context usage through strategic agent delegation.

**Strategy:**
- Use Task tool for specialized work
- Delegate research to subagents
- Avoid work duplication
- Reserve main context for decisions
- Parallel agent execution when possible`,

  tool_priority: `### Tool Usage Priority

Always prefer dedicated tools over generic commands.

**Hierarchy:**
1. Read (not cat/head/tail)
2. Edit (not sed/awk)
3. Write (not echo/heredoc)
4. Glob (not find/ls)
5. Grep (not grep/rg)

**Exception:**
Only use Bash for system commands and terminal operations that
require shell execution.`,

  minimal_reads: `### Efficient File Reading

Strategic file access to minimize token usage.

**Techniques:**
- Use offset/limit parameters for large files
- Read only necessary sections
- Parallel reads for multiple files
- Skip redundant reads
- Cache frequently accessed content`,

  session_memory: `### Persistent Memory

Cross-session learning and pattern recognition.

**Process:**
1. Auto-save insights to memory files
2. Consult memory before similar tasks
3. Update patterns as they emerge
4. Keep MEMORY.md under 200 lines

**Benefit:**
Reduces repeated research and builds project knowledge.`,

  context_limit: `### Context Management

Strategic limits on context consumption.

**Rules:**
- Set reasonable file read limits per task
- Focus on essential code sections only
- Use agents for exploratory work
- Protect main context for critical operations
- Clear stale context regularly`,

  secret_protection: `### Secret File Protection

Comprehensive security for sensitive information.

**Blocked Patterns:**
- .env* files
- *credential* files
- *secret* files
- *token* files
- *key* files
- Certificates
- Authentication files

**Security Protocol:**
1. Never display secret file contents
2. No hardcoded secrets in code
3. Use environment variables
4. Redact secrets in outputs
5. Block commits containing secrets`,

  git_safety: `### Git Safety Protocol

Prevent destructive Git operations.

**Prohibited Actions:**
- Force push to main/master
- Using --no-verify flag
- Amending published commits
- Destructive resets without confirmation

**Safe Practices:**
- Always confirm destructive operations
- Create new commits over amending
- Verify changes before pushing
- Use feature branches`,

  file_limit: `### Change Scope Limits

Controlled modification to prevent scope creep.

**Limits:**
- Maximum 3 files per session
- Minimal necessary changes only
- No unrelated refactoring
- Focus exclusively on requested changes

**Benefit:**
Maintains clear change tracking and reduces unintended side effects.`
};

// Token savings and line count per option (for stats calculation)
const OPTION_STATS = {
  fast_mode: { tokens: 15, lines: 3 },
  parallel_exec: { tokens: 25, lines: 4 },
  auto_compress: { tokens: 30, lines: 5 },
  concise: { tokens: 20, lines: 6 },
  no_emoji: { tokens: 5, lines: 2 },
  korean_explain: { tokens: 0, lines: 3 },
  bullet_points: { tokens: 10, lines: 3 },
  smart_delegation: { tokens: 35, lines: 5 },
  tool_priority: { tokens: 15, lines: 4 },
  minimal_reads: { tokens: 20, lines: 4 },
  session_memory: { tokens: 40, lines: 6 },
  context_limit: { tokens: 25, lines: 4 },
  secret_protection: { tokens: 0, lines: 8 },
  git_safety: { tokens: 0, lines: 6 },
  file_limit: { tokens: 0, lines: 3 }
};

// DOM Elements
let selectedOptions = new Set();
let checkboxes = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  setupCardClickHandlers();
  updateStats();
});

function initializeEventListeners() {
  // Checkboxes
  checkboxes = Array.from(document.querySelectorAll('.option-card input[type="checkbox"]'));
  checkboxes.forEach(cb => {
    cb.addEventListener('change', handleCheckboxChange);
  });

  // Buttons
  document.getElementById('btn-generate').addEventListener('click', generateConfig);
  document.getElementById('btn-select-all').addEventListener('click', selectAll);
  document.getElementById('btn-reset').addEventListener('click', reset);
  document.getElementById('btn-download').addEventListener('click', downloadConfig);
  document.getElementById('btn-copy-config').addEventListener('click', copyConfig);

  // Mobile menu toggle
  const navToggle = document.getElementById('nav-toggle');
  const mobileMenu = document.getElementById('mobile-menu');
  if (navToggle && mobileMenu) {
    navToggle.addEventListener('click', () => {
      mobileMenu.classList.toggle('active');
      navToggle.classList.toggle('active');
    });
  }
}

function setupCardClickHandlers() {
  const cards = document.querySelectorAll('.option-card');
  cards.forEach(card => {
    card.addEventListener('click', (e) => {
      // Don't toggle if clicking the checkbox itself
      if (e.target.type === 'checkbox') return;

      const checkbox = card.querySelector('input[type="checkbox"]');
      checkbox.checked = !checkbox.checked;
      handleCheckboxChange({ target: checkbox });
    });
  });
}

function handleCheckboxChange(e) {
  const checkbox = e.target;
  const card = checkbox.closest('.option-card');
  const value = checkbox.value;

  if (checkbox.checked) {
    selectedOptions.add(value);
    card.classList.add('selected');
  } else {
    selectedOptions.delete(value);
    card.classList.remove('selected');
  }

  updateStats();
}

function updateStats() {
  const count = selectedOptions.size;
  let totalTokens = 0;
  let totalLines = 0;

  selectedOptions.forEach(opt => {
    const stats = OPTION_STATS[opt];
    if (stats) {
      totalTokens += stats.tokens;
      totalLines += stats.lines;
    }
  });

  // Calculate percentage savings (rough estimate)
  const savingsPercent = Math.min(Math.round(totalTokens / 3), 87);

  document.getElementById('selected-count').textContent = count;
  document.getElementById('token-savings').textContent = savingsPercent + '%';
  document.getElementById('config-size').textContent = totalLines + 15; // +15 for header/footer
}

function selectAll() {
  checkboxes.forEach(cb => {
    if (!cb.checked) {
      cb.checked = true;
      cb.closest('.option-card').classList.add('selected');
      selectedOptions.add(cb.value);
    }
  });
  updateStats();
  showToast('All options selected');
}

function reset() {
  checkboxes.forEach(cb => {
    cb.checked = false;
    cb.closest('.option-card').classList.remove('selected');
  });
  selectedOptions.clear();
  updateStats();
  document.getElementById('preview-section').style.display = 'none';
  showToast('Selection reset');
}

function generateConfig() {
  if (selectedOptions.size === 0) {
    showToast('Please select at least one option', 'error');
    return;
  }

  const config = buildConfigContent();
  displayPreview(config);
  showToast('Configuration generated successfully!');
}

function buildConfigContent() {
  const date = new Date().toISOString().split('T')[0];

  const header = `# CLAUDE.md - AI Performance Configuration
# TokenSaver Pro v1.0
# Generated: ${date}
# Optimizations: ${selectedOptions.size} selected

---

## About This Configuration

This file contains optimized settings for Claude AI to maximize performance
and minimize token usage. Place this file in one of these locations:

- Global settings: ~/.claude/CLAUDE.md
- Project settings: <project-root>/.claude/CLAUDE.md

---
`;

  const sections = [];

  // Group by category for better organization
  const categories = {
    performance: [],
    style: [],
    workflow: [],
    memory: [],
    security: []
  };

  checkboxes.forEach(cb => {
    if (selectedOptions.has(cb.value)) {
      const category = cb.closest('.option-card').dataset.category;
      const template = CONFIG_TEMPLATES[cb.value];
      if (template && categories[category]) {
        categories[category].push(template);
      }
    }
  });

  // Build sections with consistent formatting
  if (categories.performance.length > 0) {
    sections.push('## [P] Performance Optimizations\n\n' + categories.performance.join('\n\n'));
  }
  if (categories.style.length > 0) {
    sections.push('## [S] Response Style\n\n' + categories.style.join('\n\n'));
  }
  if (categories.workflow.length > 0) {
    sections.push('## [W] Workflow Efficiency\n\n' + categories.workflow.join('\n\n'));
  }
  if (categories.memory.length > 0) {
    sections.push('## [M] Memory Management\n\n' + categories.memory.join('\n\n'));
  }
  if (categories.security.length > 0) {
    sections.push('## [X] Security & Safety\n\n' + categories.security.join('\n\n'));
  }

  const footer = `

---

## Configuration Info

- Product: TokenSaver Pro
- Version: 1.0
- Generated: ${date}
- Settings: ${selectedOptions.size} optimization(s) enabled

For more information, visit: https://tokensaver.pro
`;

  return header + sections.join('\n\n---\n\n') + footer;
}

function displayPreview(config) {
  const previewSection = document.getElementById('preview-section');
  const previewCode = document.getElementById('preview-code');

  previewCode.textContent = config;
  previewSection.style.display = 'block';

  // Scroll to preview
  previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function downloadConfig() {
  const config = document.getElementById('preview-code').textContent;

  const blob = new Blob([config], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'CLAUDE.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('CLAUDE.md downloaded!');
}

function copyConfig() {
  const config = document.getElementById('preview-code').textContent;

  navigator.clipboard.writeText(config).then(() => {
    showToast('Configuration copied to clipboard!');
  }).catch(err => {
    showToast('Failed to copy: ' + err.message, 'error');
  });
}

function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = 'toast show' + (type === 'error' ? ' error' : '');

  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}
