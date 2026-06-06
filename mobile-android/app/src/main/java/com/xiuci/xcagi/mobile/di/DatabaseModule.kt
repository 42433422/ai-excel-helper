package com.xiuci.xcagi.mobile.di

import android.content.Context
import androidx.room.Room
import com.xiuci.xcagi.mobile.core.db.XcagiDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDb(@ApplicationContext ctx: Context): XcagiDatabase =
        Room.databaseBuilder(ctx, XcagiDatabase::class.java, "xcagi.db")
            .fallbackToDestructiveMigration()
            .build()
}
