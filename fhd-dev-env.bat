@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo =============================================
echo FHD ������������׼�����ݿ������������������
echo =============================================

call "%~dp0scripts\docker-postgres-for-fhd.cmd"
if errorlevel 1 (
    echo [WARN] Docker Postgres ����ʧ�ܣ����������� Postgres �ɺ��ԡ�
)

call "%~dp0scripts\fhd-set-database-url.cmd"

echo =============================================
echo [OK] DATABASE_URL �� PYTHONPATH �����ڱ����ڡ�
echo      Ĭ�����ݿ��ַ: postgresql+psycopg://xcagi:***@127.0.0.1:5433/xcagi
echo      �ճ�һ��������˫��: start-fhd.bat
echo      ���ڱ������ܺ��: python -m uvicorn backend.http_app:app --host 127.0.0.1 --port 8000
echo =============================================
