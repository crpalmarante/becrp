window.ActionRegistry = class ActionRegistry {
  constructor() {
    this._actions = {};
    this._groups = {};
  }
  register(id, def) {
    this._actions[id] = {
      id,
      label: def.label || id,
      icon: def.icon || '',
      context: def.context || 'global',
      when: def.when || (() => true),
      priority: def.priority || 0,
      group: def.group || '',
      shortcut: def.shortcut || '',
      handler: def.handler || (() => {}),
      visible: def.visible !== false,
      permissions: def.permissions || [],
      data: def.data || {}
    };
    if (def.group) {
      (this._groups[def.group] = this._groups[def.group] || []).push(id);
    }
    bus.emit('action:registered', { id, def: this._actions[id] });
    return this;
  }
  unregister(id) {
    const a = this._actions[id];
    if (!a) return;
    if (a.group) {
      this._groups[a.group] = (this._groups[a.group] || []).filter(g => g !== id);
    }
    delete this._actions[id];
    bus.emit('action:unregistered', { id });
  }
  get(id) { return this._actions[id] || null; }
  list(opts) {
    let items = Object.values(this._actions);
    if (opts) {
      if (opts.context) items = items.filter(a => a.context === opts.context);
      if (opts.group) items = items.filter(a => a.group === opts.group);
      if (opts.when !== undefined) {
        const ctx = opts.contextData || {};
        items = items.filter(a => !a.when || a.when(ctx));
      }
      if (opts.visibleOnly) items = items.filter(a => a.visible);
    }
    items.sort((a, b) => b.priority - a.priority);
    return items;
  }
  getGroup(name) {
    return (this._groups[name] || []).map(id => this._actions[id]).filter(Boolean);
  }
  execute(id, ctx) {
    const a = this._actions[id];
    if (!a) { console.warn(`Action not found: ${id}`); return; }
    if (!a.when || a.when(ctx)) {
      bus.emit('action:before', { id, ctx });
      a.handler(ctx);
      bus.emit('action:after', { id, ctx });
    }
  }
  getContextualActions(context, contextData) {
    return this.list({ context, when: true, contextData, visibleOnly: true });
  }
};

window.actions = new ActionRegistry();
