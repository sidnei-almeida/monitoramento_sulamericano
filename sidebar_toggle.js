// Script para ocultar/exibir a barra lateral no Streamlit
function toggleSidebar() {
    const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
    if (sidebar) {
        if (sidebar.style.display === 'none') {
            sidebar.style.display = '';
        } else {
            sidebar.style.display = 'none';
        }
    }
}

// Adiciona botão de toggle no topo da barra lateral
function addSidebarToggleButton() {
    const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return;
    if (sidebar.querySelector('.toggle-sidebar-btn')) return;
    const btn = document.createElement('button');
    btn.innerText = 'Ocultar/Mostrar Barra Lateral';
    btn.className = 'toggle-sidebar-btn';
    btn.style.margin = '10px 0 20px 0';
    btn.style.width = '90%';
    btn.style.padding = '8px 0';
    btn.style.background = '#1565c0';
    btn.style.color = '#fff';
    btn.style.border = 'none';
    btn.style.borderRadius = '8px';
    btn.style.fontWeight = 'bold';
    btn.style.cursor = 'pointer';
    btn.onclick = toggleSidebar;
    sidebar.insertBefore(btn, sidebar.firstChild);
}

window.addEventListener('DOMContentLoaded', addSidebarToggleButton);
setTimeout(addSidebarToggleButton, 1000); // fallback para garantir que o botão aparece
