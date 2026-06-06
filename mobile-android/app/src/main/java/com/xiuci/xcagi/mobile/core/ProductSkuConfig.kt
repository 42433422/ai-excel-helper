package com.xiuci.xcagi.mobile.core

import com.xiuci.xcagi.mobile.BuildConfig

/** 安装包 SKU：与桌面 personal / enterprise 对齐。 */
object ProductSkuConfig {
    val sku: String get() = BuildConfig.PRODUCT_SKU

    val isEnterprise: Boolean get() = sku == "enterprise"

    val isPersonal: Boolean get() = sku == "personal"

    /** 个人版隐藏 ERP / 审批等企业向底部导航。 */
    val showsEnterpriseNav: Boolean get() = isEnterprise

    val accountKind: String get() = if (isEnterprise) "enterprise" else "personal"

    val displayEditionLabel: String get() = if (isEnterprise) "企业版" else "个人版"
}
