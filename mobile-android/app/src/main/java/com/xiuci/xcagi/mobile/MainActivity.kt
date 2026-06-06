package com.xiuci.xcagi.mobile

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.fragment.app.FragmentActivity
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.hilt.navigation.compose.hiltViewModel
import com.xiuci.xcagi.mobile.core.security.BiometricGate
import com.xiuci.xcagi.mobile.navigation.XcagiNavHost
import com.xiuci.xcagi.mobile.ui.AppViewModel
import com.xiuci.xcagi.mobile.ui.theme.XcagiTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : FragmentActivity() {
    private var unlocked = false

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleIntent(intent)
        setContent {
            val vm: AppViewModel = hiltViewModel()
            val themeMode by vm.themeMode.collectAsState()
            val biometric by vm.biometricEnabled.collectAsState()
            XcagiTheme(themeMode = themeMode) {
                if (biometric && !unlocked && BiometricGate.canAuthenticate(this)) {
                    BiometricGate.prompt(
                        this,
                        onSuccess = { unlocked = true },
                        onError = { finish() },
                    )
                } else {
                    XcagiNavHost(vm, pendingDeepLink)
                }
            }
        }
    }

    private var pendingDeepLink: String? = null

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val route = intent?.getStringExtra("deep_link_route")
        if (!route.isNullOrBlank()) {
            pendingDeepLink = route
            return
        }
        val data: Uri? = intent?.data
        if (data != null) {
            pendingDeepLink = when {
                data.scheme == "xcagi" -> data.host.orEmpty().let { h ->
                    data.path?.let { p -> "$h$p" } ?: h
                }
                data.host?.contains("xiu-ci.com") == true -> data.path ?: "/app/workbench"
                else -> null
            }
        }
    }
}
