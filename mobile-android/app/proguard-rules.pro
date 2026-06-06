-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

-keep class com.xiuci.xcagi.mobile.core.model.** { *; }
-keep class com.xiuci.xcagi.mobile.core.network.** { *; }

-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}

-keep class com.google.gson.** { *; }
-keep class * extends com.google.gson.TypeAdapter

-dontwarn okhttp3.**
-dontwarn cn.jpush.**

-keep class cn.jpush.** { *; }
-keep class cn.jiguang.** { *; }

-keep class com.google.firebase.** { *; }
