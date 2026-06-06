<template>
  <div class="template-media-preview" :class="rootClass">
    <ExcelPreview
      v-if="resolvedMediaKind === 'excel' && showExcelGrid"
      :fields="fields"
      :sample-rows="sampleRows"
      :title="excelTitle"
      :grid-data="gridData"
      :rows="rows"
      :columns="columns"
    />
    <div v-else-if="isVirtualPlaceholder" class="tp-card-placeholder">
      <span class="tp-placeholder-title">待上传模板</span>
      <span v-if="requiredTerms.length" class="tp-placeholder-terms">
        必备词条：{{ requiredTerms.join('、') }}
      </span>
      <span v-else class="tp-placeholder-terms muted">{{ uploadHint }}</span>
    </div>
    <div v-else-if="resolvedMediaKind === 'label'" class="tp-card-placeholder">
      <LabelPreview :fields="fields" :width="labelWidth" :height="labelHeight" />
    </div>
    <div v-else class="tp-card-placeholder" :class="`tp-card-placeholder--${mediaKind}`">
      <i class="fa" :class="iconClass" aria-hidden="true"></i>
      <span class="tmp-file-name">{{ displayName }}</span>
      <span v-if="statusHint" class="tmp-status muted">{{ statusHint }}</span>
    </div>
  </div>
</template>

<script>
import ExcelPreview from '@/components/template/ExcelPreview.vue'
import LabelPreview from '@/components/template/LabelPreview.vue'
import {
  isTemplateMediaKind,
  normalizeTemplateMediaKind,
  templateMediaIconClass,
  templateMediaUploadHint,
} from '@/constants/templateMediaKinds'

export default {
  name: 'TemplateMediaPreview',
  components: { ExcelPreview, LabelPreview },
  props: {
    template: { type: Object, default: null },
    mediaKind: { type: String, default: '' },
    virtual: { type: Boolean, default: false },
    showExcelGrid: { type: Boolean, default: false },
    fields: { type: Array, default: () => [] },
    sampleRows: { type: Array, default: () => [] },
    gridData: { type: Object, default: null },
    excelTitle: { type: String, default: 'Excel 预览' },
    requiredTerms: { type: Array, default: () => [] },
    displayName: { type: String, default: '' },
    statusHint: { type: String, default: '' },
    rows: { type: Number, default: 5 },
    columns: { type: Number, default: 5 },
    labelWidth: { type: Number, default: 280 },
    labelHeight: { type: Number, default: 180 },
    compact: { type: Boolean, default: false },
  },
  computed: {
    isVirtualPlaceholder() {
      return Boolean(this.virtual) && !this.showExcelGrid && this.resolvedMediaKind !== 'label'
    },
    iconClass() {
      return templateMediaIconClass(this.resolvedMediaKind)
    },
    uploadHint() {
      return templateMediaUploadHint()
    },
    rootClass() {
      return {
        'template-media-preview--compact': this.compact,
        [`template-media-preview--${this.resolvedMediaKind}`]: Boolean(this.resolvedMediaKind),
      }
    },
    resolvedMediaKind() {
      const fromProp = String(this.mediaKind || '').trim()
      if (isTemplateMediaKind(fromProp)) return fromProp
      const fromTpl = String(this.template?.category || '').trim()
      if (fromTpl === 'label') return 'label'
      return normalizeTemplateMediaKind(fromTpl, 'excel')
    },
  },
}
</script>

<style scoped>
.template-media-preview {
  width: 100%;
  min-height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.template-media-preview--compact {
  min-height: 72px;
}

.tp-card-placeholder {
  width: 100%;
  min-height: 96px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}

.tp-card-placeholder .fa {
  font-size: 28px;
  opacity: 0.88;
}

.tp-card-placeholder--excel .fa { color: #15803d; }
.tp-card-placeholder--word .fa { color: #2b579a; }
.tp-card-placeholder--csv .fa { color: #0369a1; }
.tp-card-placeholder--ppt .fa { color: #c2410c; }
.tp-card-placeholder--pdf .fa { color: #b91c1c; }

.tmp-file-name {
  font-weight: 500;
  color: #334155;
  word-break: break-all;
}

.tmp-status {
  font-size: 11px;
  line-height: 1.4;
}
</style>
