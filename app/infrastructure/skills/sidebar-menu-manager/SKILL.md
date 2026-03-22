---
name: "sidebar-menu-manager"
description: "Manages sidebar menu div with add, remove, update, and reorder menu items. Invoke when user wants to modify sidebar menu items or manage the menu structure."
---

# Sidebar Menu Manager

This skill manages the sidebar menu component (`Sidebar.vue`) which contains a list of `menu-item` buttons for navigation.

## Component Location

- **File**: `frontend/src/components/Sidebar.vue`
- **Menu Container**: `<div class="sidebar-menu">` containing `<button>` elements
- **Menu Items Data**: `menuItems` array in the script section

## Menu Item Structure

Each menu item is an object with:
```javascript
{ key: 'unique-key', name: 'Display Name', icon: 'emoji' }
```

## Operations

### Add Menu Item

Add new item to `menuItems` array:
```javascript
menuItems.push({ key: 'new-key', name: '新菜单项', icon: '➕' })
```

### Remove Menu Item

Remove item by key:
```javascript
const index = menuItems.findIndex(item => item.key === 'target-key')
if (index > -1) menuItems.splice(index, 1)
```

### Update Menu Item

Update item properties by key:
```javascript
const item = menuItems.find(item => item.key === 'target-key')
if (item) {
  item.name = '新名称'
  item.icon = '🆕'
}
```

### Reorder Menu Items

Splice to remove and insert at new position:
```javascript
const index = menuItems.findIndex(item => item.key === 'item-key')
const [item] = menuItems.splice(index, 1)
menuItems.splice(newIndex, 0, item)
```

## Vue Reactivity Notes

Since `menuItems` is a `ref`, use `.value` when modifying programmatically:
```javascript
menuItems.value.push({...})     // add
menuItems.value.splice(...)     // remove/update/reorder
```

## File Path

The skill manages: `e:\FHD\XCAGI\frontend\src\components\Sidebar.vue`
