from django.urls import path
from . import views

app_name = 'audio_analyzer'

urlpatterns = [
    # Home/Index page
    path('', views.index, name='index'),
    
    # Audio recording endpoint
    path('record/', views.record_audio, name='record_audio'),
    
    # Spectrogram generation endpoint
    path('spectrogram/', views.generate_spectrogram, name='generate_spectrogram'),
    
    # Analysis results endpoint
    path('analyze/', views.analyze_audio, name='analyze_audio'),
    
    # Multi-recording and spectrogram generation endpoint
    path('multi-record/', views.record_and_generate_spectrograms, name='record_and_generate_spectrograms'),
    
    # Audio devices listing endpoint
    path('devices/', views.get_audio_devices, name='get_audio_devices'),
    
    # Predictors analysis page
    path('predictors/', views.predictors_view, name='predictors'),
]
