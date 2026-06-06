package com.xiuci.xcagi.mobile.feature.scan

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.xiuci.xcagi.mobile.ui.AppViewModel
import java.util.concurrent.Executors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanQrScreen(vm: AppViewModel, onBack: () -> Unit) {
    val ctx = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var nonce by remember { mutableStateOf("") }
    var scanned by remember { mutableStateOf(false) }
    var hasCamera by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED,
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> hasCamera = granted }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text("扫描配对码") })
        if (hasCamera) {
            Box(Modifier.weight(1f)) {
                AndroidView(
                    factory = { PreviewView(it) },
                    modifier = Modifier.fillMaxSize(),
                ) { previewView ->
                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                    cameraProviderFuture.addListener({
                        val cameraProvider = cameraProviderFuture.get()
                        val preview = Preview.Builder().build().also {
                            it.surfaceProvider = previewView.surfaceProvider
                        }
                        val analyzer = ImageAnalysis.Builder().build().also { analysis ->
                            analysis.setAnalyzer(Executors.newSingleThreadExecutor()) { imageProxy ->
                                if (scanned) {
                                    imageProxy.close()
                                    return@setAnalyzer
                                }
                                val mediaImage = imageProxy.image
                                if (mediaImage != null) {
                                    val image = InputImage.fromMediaImage(
                                        mediaImage,
                                        imageProxy.imageInfo.rotationDegrees,
                                    )
                                    BarcodeScanning.getClient().process(image)
                                        .addOnSuccessListener { barcodes ->
                                            val raw = barcodes.firstOrNull()?.rawValue
                                            if (!raw.isNullOrBlank()) {
                                                scanned = true
                                                nonce = raw
                                                vm.exchangeQr(raw) { ok ->
                                                    if (ok) {
                                                        vm.completeSetup()
                                                        onBack()
                                                    } else {
                                                        scanned = false
                                                    }
                                                }
                                            }
                                        }
                                        .addOnCompleteListener { imageProxy.close() }
                                } else {
                                    imageProxy.close()
                                }
                            }
                        }
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(
                            lifecycleOwner,
                            CameraSelector.DEFAULT_BACK_CAMERA,
                            preview,
                            analyzer,
                        )
                    }, ContextCompat.getMainExecutor(ctx))
                }
            }
        } else {
            Text(
                "需要相机权限以扫描电脑端配对二维码",
                modifier = Modifier.padding(16.dp),
            )
            Button({ permissionLauncher.launch(Manifest.permission.CAMERA) }, Modifier.padding(16.dp)) {
                Text("授予相机权限")
            }
        }
        OutlinedTextField(
            nonce,
            { nonce = it },
            Modifier.fillMaxWidth().padding(16.dp),
            label = { Text("或手动粘贴 nonce") },
        )
        Button(
            {
                vm.exchangeQr(nonce) {
                    if (it) {
                        vm.completeSetup()
                        onBack()
                    }
                }
            },
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        ) { Text("配对") }
    }
}
