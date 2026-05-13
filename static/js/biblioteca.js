/**
 * biblioteca.js
 * Lógica da página de Biblioteca de Matrizes.
 *
 * Responsabilidades:
 *  - Filtrar e renderizar os cards da grade
 *  - Exibir o painel de detalhes ao selecionar uma matriz
 *  - Atualizar a cor de um swatch em tempo real
 */

// ─────────────────────────────────────────────
// Estado global da página
// ─────────────────────────────────────────────
let activeFilter = 'Todos';
let selectedId   = null;

function toggleTheme() {
    document.body.classList.toggle("dark");
}
// ─────────────────────────────────────────────
// Filtros
// ─────────────────────────────────────────────

/** Define a categoria ativa e re-renderiza os cards. */
function setFilter(filter) {
  activeFilter = filter;

  document.querySelectorAll('.chip').forEach(chip => {
    chip.classList.toggle('active', chip.textContent === filter);
  });

  filterCards();
}

/**
 * Aplica o filtro de categoria + texto de busca,
 * atualiza os contadores e re-renderiza a grade.
 */
function filterCards() {
  const query = document.getElementById('search-input').value.toLowerCase();

  const filtered = matrices.filter(m => {
    const matchCategory = activeFilter === 'Todos' || m.categoria === activeFilter;
    const matchQuery    = !query
      || m.nome.toLowerCase().includes(query)
      || m.categoria.toLowerCase().includes(query)
      || m.tema.toLowerCase().includes(query);

    return matchCategory && matchQuery;
  });

  document.getElementById('results-label').textContent =
    `${filtered.length} matriz(es) encontrada(s)`;
  document.getElementById('total-count').textContent = matrices.length;

  renderGrid(filtered);
}

// ─────────────────────────────────────────────
// Renderização da Grade
// ─────────────────────────────────────────────

/**
 * Gera o HTML dos cards e insere na grade.
 * @param {Array} list - Lista de matrizes filtradas
 */
function renderGrid(list) {
  const grid        = document.getElementById('matrix-grid');
  const cacheBuster = Date.now();

  grid.innerHTML = list.map(m => {
    const colorDots = m.cores.slice(0, 4)
      .map(c => `<div class="color-dot" style="background:${c.hex}"></div>`)
      .join('');

    const isSelected = selectedId === m.id ? ' selected' : '';

    return `
      <div class="matrix-card${isSelected}" id="card-${m.id}" onclick="selectMatrix('${m.id}')">
        <div class="card-thumb">
          <img src="${m.png_url}?t=${cacheBuster}" alt="${m.nome}">
        </div>
        <div class="card-info">
          <div class="card-name">${m.nome}</div>
          <div class="card-meta">${m.pontos.toLocaleString('pt-BR')} pts · ${m.categoria}</div>
          <div class="card-colors">${colorDots}</div>
        </div>
      </div>`;
  }).join('');
}

// ─────────────────────────────────────────────
// Painel de Detalhes
// ─────────────────────────────────────────────

/**
 * Seleciona uma matriz, atualiza o card ativo
 * e preenche o painel lateral com os detalhes.
 * @param {string} id - ID da matriz
 */
function selectMatrix(id) {
  selectedId = id;
  filterCards(); // re-renderiza para marcar o card como selecionado

  const m = matrices.find(x => x.id === id);
  if (!m) return;

  const cacheBuster = Date.now();

  document.getElementById('panel-content').innerHTML = `
    ${buildPanelHeader(m)}
    ${buildPanelPreview(m, cacheBuster)}
    ${buildPanelInfo(m)}
    ${buildPanelColors(m)}
    ${buildPanelActions(m)}
  `;
}

/** Cabeçalho do painel: nome e arquivo */
function buildPanelHeader(m) {
  return `
    <div class="panel-header">
      <div class="panel-title">${m.nome}</div>
      <div class="panel-subtitle">${m.categoria} · ${m.arquivo}</div>
    </div>`;
}

/** Preview da imagem no painel */
function buildPanelPreview(m, cacheBuster) {
  return `
    <div class="panel-preview">
      <img src="${m.png_url}?t=${cacheBuster}" alt="${m.nome}">
    </div>`;
}

/** Informações técnicas: pontos, dimensões, tema, qtd. cores */
function buildPanelInfo(m) {
  return `
    <div class="panel-section">
      <div class="panel-section-title">Informações Técnicas</div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Pontos</span>
          <span class="info-value">${m.pontos.toLocaleString('pt-BR')}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Dimensões</span>
          <span class="info-value">${m.dimensoes}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Tema</span>
          <span class="info-value">${m.tema}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Qtd. Cores</span>
          <span class="info-value">${m.cores.length}</span>
        </div>
      </div>
    </div>`;
}

/** Lista de cores editáveis */
function buildPanelColors(m) {
  const rows = m.cores.map((c, i) => `
    <div class="color-row">
      <div class="color-swatch" style="background:${c.hex}">
        <input type="color" name="color_${i}" value="${c.hex}"
               onchange="updateSwatch(this, '${m.id}', ${i})" />
      </div>
      <div class="color-name">${c.nome}</div>
      <span class="color-hex" id="hex-${m.id}-${i}">${c.hex}</span>
    </div>`).join('');

  return `
    <form action="/update_colors/${m.id}" method="POST" class="panel-colors-form">
      <div class="panel-section">
        <div class="panel-section-title">Cores — Altere e salve o preview</div>
        <div class="color-list">${rows}</div>
      </div>
      <div class="panel-actions">
        <button type="submit" class="btn-primary btn-full">Salvar Novas Cores</button>
      </div>
    </form>`;
}

/** Botão de deletar (form separado para não conflitar com o de cores) */
function buildPanelActions(m) {
  return `
    <div class="panel-actions panel-actions--delete">
      <form action="/delete/${m.id}" method="POST">
        <button type="submit" class="btn-outline btn-danger btn-full"
                onclick="return confirm('Excluir matriz?')">
          Excluir Matriz
        </button>
      </form>
    </div>`;
}

// ─────────────────────────────────────────────
// Atualização de Swatch em tempo real
// ─────────────────────────────────────────────

/**
 * Atualiza a cor do swatch e o label hex sem precisar salvar.
 * @param {HTMLInputElement} input
 * @param {string} matrixId
 * @param {number} colorIndex
 */
function updateSwatch(input, matrixId, colorIndex) {
  const hex      = input.value;
  const hexLabel = document.getElementById(`hex-${matrixId}-${colorIndex}`);

  if (hexLabel) hexLabel.textContent = hex;
  input.parentElement.style.background = hex;
}

// ─────────────────────────────────────────────
// Janela Modal para nova matriz
// ─────────────────────────────────────────────
function openNewMatrixModal() {
  document.getElementById('novaModal').classList.add('open');
}

function closeNewMatrixModal() {
  document.getElementById('novaModal').classList.remove('open');
}

// ─────────────────────────────────────────────
// Inicialização
// ─────────────────────────────────────────────
filterCards();