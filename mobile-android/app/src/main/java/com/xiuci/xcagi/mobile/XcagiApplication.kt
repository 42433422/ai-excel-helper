package com.xiuci.xcagi.mobile

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.xiuci.xcagi.mobile.core.push.PushRegistrar
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class XcagiApplication : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory
    @Inject lateinit var pushRegistrar: PushRegistrar

    override fun onCreate() {
        super.onCreate()
        pushRegistrar.initSdk()
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setWorkerFactory(workerFactory).build()
}
