import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}

android {
    namespace = "com.xiuci.xcagi.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.xiuci.xcagi.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 9
        versionName = "1.4.0"
        manifestPlaceholders["JPUSH_PKGNAME"] = "com.xiuci.xcagi.mobile"
        manifestPlaceholders["JPUSH_CHANNEL"] = "developer-default"
        manifestPlaceholders["JPUSH_APPKEY"] = "placeholder_replace_in_local_properties"
        buildConfigField("int", "FHD_DEFAULT_PORT", "5000")
        buildConfigField("String", "MODSTORE_BASE_URL", "\"https://xiu-ci.com\"")
        buildConfigField("String", "COMPANY_NAME", "\"成都修茈科技有限公司\"")
    }

    flavorDimensions += "sku"
    productFlavors {
        create("personal") {
            dimension = "sku"
            applicationIdSuffix = ".personal"
            resValue("string", "app_name", "XCAGI 个人版")
            buildConfigField("String", "PRODUCT_SKU", "\"personal\"")
            manifestPlaceholders["JPUSH_PKGNAME"] = "com.xiuci.xcagi.mobile.personal"
        }
        create("enterprise") {
            dimension = "sku"
            applicationIdSuffix = ".enterprise"
            resValue("string", "app_name", "XCAGI 企业版")
            buildConfigField("String", "PRODUCT_SKU", "\"enterprise\"")
            manifestPlaceholders["JPUSH_PKGNAME"] = "com.xiuci.xcagi.mobile.enterprise"
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    signingConfigs {
        create("release") {
            val keystoreProps = Properties()
            val propsFile = rootProject.file("keystore.properties")
            if (propsFile.isFile) {
                propsFile.inputStream().use { keystoreProps.load(it) }
            }

            fun prop(name: String): String? =
                System.getenv("XCAGI_ANDROID_${name.uppercase()}")?.takeIf { it.isNotBlank() }
                    ?: keystoreProps.getProperty(
                        when (name) {
                            "KEYSTORE" -> "storeFile"
                            "KEYSTORE_PASSWORD" -> "storePassword"
                            "KEY_ALIAS" -> "keyAlias"
                            "KEY_PASSWORD" -> "keyPassword"
                            else -> name
                        },
                    )?.trim()?.takeIf { it.isNotBlank() }

            val storePath = prop("KEYSTORE")
            if (!storePath.isNullOrBlank()) {
                val resolved = rootProject.file(storePath)
                if (!resolved.isFile) {
                    throw GradleException("Release keystore not found: ${resolved.absolutePath}")
                }
                storeFile = resolved
                storePassword = prop("KEYSTORE_PASSWORD")
                keyAlias = prop("KEY_ALIAS")
                keyPassword = prop("KEY_PASSWORD") ?: prop("KEYSTORE_PASSWORD")
                if (storePassword.isNullOrBlank() || keyAlias.isNullOrBlank()) {
                    throw GradleException(
                        "Release signing incomplete: set storePassword and keyAlias in keystore.properties or XCAGI_ANDROID_* env vars.",
                    )
                }
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            val releaseSigning = signingConfigs.getByName("release")
            val requireSigning = System.getenv("XCAGI_REQUIRE_RELEASE_SIGNING") == "1"
            signingConfig = when {
                releaseSigning.storeFile != null -> releaseSigning
                requireSigning -> throw GradleException(
                    "XCAGI_REQUIRE_RELEASE_SIGNING=1 but no release keystore configured. " +
                        "Run scripts/package/new-android-release-keystore.ps1 or set XCAGI_ANDROID_KEYSTORE*.",
                )
                else -> signingConfigs.getByName("debug")
            }
        }
    }
}

tasks.matching { it.name.startsWith("assemble") && it.name.contains("Release") }.configureEach {
    doFirst {
        val releaseSigning = android.signingConfigs.getByName("release")
        if (releaseSigning.storeFile == null) {
            logger.warn(
                "XCAGI Release: no release keystore — APK will be signed with DEBUG key. " +
                    "Copy keystore.properties.example → keystore.properties or run new-android-release-keystore.ps1",
            )
        } else {
            logger.lifecycle("XCAGI Release: signing with ${releaseSigning.storeFile}")
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.navigation:navigation-compose:2.8.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.hilt:hilt-work:1.2.0")
    ksp("androidx.hilt:hilt-compiler:1.2.0")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    implementation("com.google.dagger:hilt-android:2.52")
    ksp("com.google.dagger:hilt-android-compiler:2.52")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.squareup.okhttp3:okhttp-sse:4.12.0")

    val camerax = "1.4.0"
    implementation("androidx.camera:camera-camera2:$camerax")
    implementation("androidx.camera:camera-lifecycle:$camerax")
    implementation("androidx.camera:camera-view:$camerax")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")

    implementation("androidx.webkit:webkit:1.12.1")
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    val firebaseBom = platform("com.google.firebase:firebase-bom:33.7.0")
    implementation(firebaseBom)
    implementation("com.google.firebase:firebase-crashlytics")
    implementation("com.google.firebase:firebase-analytics")
    implementation("com.google.firebase:firebase-messaging")

    implementation("cn.jiguang.sdk:jpush:5.6.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.9.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
}

val localProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.isFile) f.inputStream().use { load(it) }
}
val jpushKey = localProps.getProperty("JPUSH_APPKEY")?.trim().orEmpty()
if (jpushKey.isNotBlank()) {
    android.defaultConfig.manifestPlaceholders["JPUSH_APPKEY"] = jpushKey
}
