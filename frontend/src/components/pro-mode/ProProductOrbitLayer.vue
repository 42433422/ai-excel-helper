<template>
  <div 
    class="pro-product-orbit-layer"
    :style="{ 
      transform: `scale(${orbitScale})`,
      opacity: stage === 'idle' ? 0 : 1
    }"
  >
    <div 
      v-if="stage === 'companies'"
      class="orbit-ring company-ring"
      :style="{ 
        animationDuration: '30s',
        animationDelay: '0s'
      }"
    >
      <div 
        v-for="(company, index) in companies" 
        :key="'company-' + index"
        class="orbit-item company-item"
        :style="{ 
          transform: `rotate(${(index / companies.length) * 360}deg) translateX(${radius}px)`,
          animationDelay: `${index * 0.1}s`
        }"
        @click="handleCompanyClick(company)"
      >
        <div class="company-label">{{ company.name }}</div>
      </div>
    </div>
    
    <div 
      v-if="stage === 'company_selected'"
      class="product-rings-container"
    >
      <div 
        v-for="(productRing, ringIndex) in productRings" 
        :key="'product-ring-' + ringIndex"
        class="orbit-ring product-ring"
        :style="{ 
          width: `${radius * 2}px`,
          height: `${radius * 2}px`,
          animationDuration: '25s',
          animationDelay: `${ringIndex * 0.15}s`
        }"
      >
        <div 
          v-for="(product, index) in productRing" 
          :key="'product-' + ringIndex + '-' + index"
          class="orbit-item product-item"
          :style="{ 
            transform: `rotate(${(index / productRing.length) * 360}deg) translateX(${radius}px)`,
            animationDelay: `${(ringIndex * 0.1 + index * 0.05)}s`
          }"
          @click="handleProductClick(product)"
        >
          <div class="product-label">{{ product.name }}</div>
        </div>
      </div>
    </div>
    
    <div 
      v-if="stage === 'product_selected'"
      class="selected-product-display"
    >
      <div class="selected-product-info">
        <div class="product-name">{{ selectedProduct?.name }}</div>
        <div class="product-details">
          <div class="product-detail">
            <span class="detail-label">型号：</span>
            <span class="detail-value">{{ selectedProduct?.model }}</span>
          </div>
          <div class="product-detail">
            <span class="detail-label">单价：</span>
            <span class="detail-value">¥{{ selectedProduct?.price }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stage: {
    type: String,
    default: 'idle'
  },
  companies: {
    type: Array,
    default: () => []
  },
  products: {
    type: Array,
    default: () => []
  },
  selectedCompany: {
    type: Object,
    default: null
  },
  selectedProduct: {
    type: Object,
    default: null
  },
  orbitScale: {
    type: Number,
    default: 1
  },
  radius: {
    type: Number,
    default: 260
  }
})

const emit = defineEmits(['companySelect', 'productSelect', 'reset'])

const productRings = computed(() => {
  if (props.selectedCompany) {
    const companyProducts = props.products.filter(p => p.companyId === props.selectedCompany.id)
    const rings = []
    const productsPerRing = 8
    
    for (let i = 0; i < companyProducts.length; i += productsPerRing) {
      rings.push(companyProducts.slice(i, i + productsPerRing))
    }
    
    return rings
  }
  
  return []
})

function handleCompanyClick(company) {
  emit('companySelect', company)
}

function handleProductClick(product) {
  emit('productSelect', product)
}
</script>

<style scoped>
.pro-product-orbit-layer {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  pointer-events: none;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.orbit-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(0, 255, 255, 0.3);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.orbit-ring.company-ring {
  width: 520px;
  height: 520px;
  animation: spin 30s linear infinite;
}

.orbit-ring.product-ring {
  animation: spin 25s linear infinite;
}

.orbit-item {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.orbit-item:hover {
  transform: translate(-50%, -50%) scale(1.2);
}

.company-item {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.4);
}

.product-item {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.15);
  border: 1px solid rgba(0, 255, 255, 0.3);
}

.company-label,
.product-label {
  color: rgba(0, 255, 255, 0.9);
  font-size: 12px;
  font-weight: bold;
  text-align: center;
  white-space: nowrap;
  text-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
}

.product-rings-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
}

.selected-product-display {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: auto;
}

.selected-product-info {
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 12px;
  padding: 20px;
  min-width: 200px;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  animation: scaleIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.product-name {
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
  margin-bottom: 12px;
  text-align: center;
}

.product-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  color: rgba(0, 255, 255, 0.7);
  font-size: 14px;
}

.detail-value {
  color: rgba(0, 255, 255, 0.9);
  font-size: 14px;
  font-weight: bold;
}

@keyframes spin {
  from {
    transform: translate(-50%, -50%) rotateZ(0deg);
  }
  to {
    transform: translate(-50%, -50%) rotateZ(360deg);
  }
}

@keyframes scaleIn {
  from {
    transform: translate(-50%, -50%) scale(0);
    opacity: 0;
  }
  to {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
}
</style>
