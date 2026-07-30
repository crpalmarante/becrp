# Biblioteca de Componentes — Status Real

Situação atual dos componentes implementados no FiscalUI.

## Layout

| Componente | Status | Sprint | Arquivo |
|-----------|--------|--------|---------|
| TopBar/Header | ✅ | 02 | `js/components/Header.js` |
| Sidebar | ✅ | 02 | `js/components/Sidebar.js` |
| Toolbar | ✅ | 02 | `js/components/Toolbar.js` |
| StatusBar | ✅ | 02 | nativo no `index4.html` |
| Breadcrumb | ✅ | 03 | `Header.setBreadcrumb()` |
| Search | ✅ | 03 | `.topbar-search` no HTML |
| Tabs | ✅ | 04 | `js/components/Tabs.js` |
| Accordion | ✅ | 04 | `js/components/Accordion.js` |
| Footer | ⬜ | — | Pendente |
| Drawer | ⬜ | — | Pendente |
| Splitter | ⬜ | — | Pendente |

## Formulários

| Componente | Status | Sprint | Arquivo |
|-----------|--------|--------|---------|
| FormService | ✅ | 02 | `js/services/FormService.js` |
| Input | ✅ | nativo | CSS `.form-input` |
| Select | ✅ | nativo | CSS `.form-select` |
| Textarea | ✅ | nativo | CSS `.form-textarea` |
| Checkbox | ✅ | nativo | CSS `.form-checkbox` |
| Radio | ⬜ | — | Pendente |
| Date | ⬜ | — | Pendente (DatePicker) |
| Upload | ⬜ | — | Pendente |
| Color Picker | ⬜ | — | Pendente |
| Editor | ⬜ | — | Pendente |

## Dados

| Componente | Status | Sprint | Arquivo |
|-----------|--------|--------|---------|
| Dashboard | ✅ | 03 | `js/components/Dashboard.js` |
| KPI Card | ✅ | 03 | nativo no Dashboard |
| WidgetManager | ✅ | 03 | `js/components/WidgetManager.js` |
| Data Grid | ⬜ | — | Pendente |
| Tree | ⬜ | — | Pendente |
| Kanban | ⬜ | — | Pendente |
| Calendar | ⬜ | — | Pendente |
| Timeline | ⬜ | — | Pendente |
| Pivot | ⬜ | — | Pendente |
| Chart | ⬜ | — | Pendente |

## Feedback

| Componente | Status | Sprint | Arquivo |
|-----------|--------|--------|---------|
| Toast | ✅ | 04 | `js/services/ToastService.js` |
| Dialog/Alert/Confirm | ✅ | 04 | `js/components/Dialog.js` |
| Prompt | ✅ | 04 | `Dialog.prompt()` |
| Loading | ✅ | 04 | `js/services/LoadingService.js` |
| Skeleton | ✅ | 04 | `js/components/Skeleton.js` |
| Badge | ✅ | 04 | `js/components/Badge.js` |
| Tag | ✅ | 04 | `Badge.tag()` |
| Notification | ⬜ | — | Pendente |
| Progress | ⬜ | — | Pendente |

## Temas & Motor

| Componente | Status | Sprint | Arquivo |
|-----------|--------|--------|---------|
| ThemeEngine | ✅ | 05 | `css/themes.css` + `[data-theme]` |
| ThemeManager | ✅ | 05 | `js/services/ThemeManager.js` |
| Theme Switcher UI | ✅ | 05 | dropdown no topbar |
| Motion Design | ✅ | 05 | `css/motion.css` + transições |
| Página Showcase | ✅ | 05 | rota `/showcase` |

## Serviços

| Serviço | Status | Sprint | Arquivo |
|---------|--------|--------|---------|
| EventManager | ✅ | 01 | `js/events/EventManager.js` |
| StateManager | ✅ | 01 | `js/state/StateManager.js` |
| StorageService | ✅ | 01 | `js/services/StorageService.js` |
| ToastService | ✅ | 02 | `js/services/ToastService.js` |
| LoadingService | ✅ | 02 | `js/services/LoadingService.js` |
| ModalService | ✅ | 02 | `js/services/ModalService.js` |
| ErrorManager | ✅ | 02 | `js/services/ErrorManager.js` |
| FormService | ✅ | 02 | `js/services/FormService.js` |
| IconManager | ✅ | 02 | `js/services/IconManager.js` |
| ThemeManager | ✅ | 05 | `js/services/ThemeManager.js` |
| Router | ✅ | 02 | `js/router/Router.js` |
| ResponsiveEngine | ✅ | 02 | `js/responsive/ResponsiveEngine.js` |
| AccessibilityEngine | ✅ | 02 | `js/accessibility/AccessibilityEngine.js` |
| PluginManager | ✅ | 02 | `js/plugins/PluginManager.js` |
| ShortcutsPlugin | ✅ | 02 | `js/plugins/ShortcutsPlugin.js` |

**Total: ~50 componentes planejados — ~30 implementados**
