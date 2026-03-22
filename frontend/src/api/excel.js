import api from './index';

function normalizeTemplateDto(tpl = {}) {
  const templateType = String(tpl.template_type || '');
  const inferCategory =
    /(标签|label|print|打印)/i.test(templateType) ? 'label_print' : 'excel';
  const filePath = tpl.file_path || tpl.path || '';
  return {
    ...tpl,
    id: String(tpl.id ?? ''),
    name: tpl.name || tpl.template_name || tpl.filename || '未命名模板',
    category: tpl.category || inferCategory,
    template_type: tpl.template_type || '',
    file_path: filePath,
    is_active: Boolean(tpl.is_active ?? true),
    preview_capable: Boolean(tpl.preview_capable ?? (tpl.exists && filePath)),
    source: tpl.source || 'db'
  };
}

export const excelApi = {
  async getTemplates(params = {}) {
    const res = await api.get('/api/excel/templates', params);
    const templates = Array.isArray(res?.templates) ? res.templates : [];
    return {
      ...res,
      templates: templates.map(normalizeTemplateDto)
    };
  },

  saveTemplate(data) {
    return api.post('/api/excel/template/save', data);
  },

  decomposeTemplate(data) {
    return api.post('/api/excel/template/decompose', data);
  },

  uploadExcel(formData) {
    return api.post('/api/excel/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  extractData(data) {
    return api.post('/api/excel/data/extract', data);
  },

  generateExcel(data) {
    return api.post('/api/excel/data/generate', data);
  },

  normalizeTemplateDto
};

export function normalizeTemplateDtoList(items = []) {
  return (Array.isArray(items) ? items : []).map(normalizeTemplateDto);
  }

export default excelApi;
