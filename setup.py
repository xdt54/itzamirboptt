import subprocess
import sys
import os


def check_python_version():
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 یا بالاتر نیاز است!")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def install_requirements():
    print("\n📦 نصب وابستگی‌ها...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ وابستگی‌ها با موفقیت نصب شدند")
    except subprocess.CalledProcessError:
        print("❌ خطا در نصب وابستگی‌ها")
        sys.exit(1)


def check_env_file():
    if not os.path.exists(".env"):
        print("\n⚠️ فایل .env یافت نشد!")
        print("📝 فایل .env.example را به .env کپی کنید و توکن بات را وارد کنید.")
        
        try:
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ فایل .env ایجاد شد. لطفاً توکن بات را در آن وارد کنید.")
        except Exception as e:
            print(f"❌ خطا در ایجاد فایل .env: {e}")
        
        sys.exit(1)
    print("✅ فایل .env موجود است")


def main():
    print("=" * 50)
    print("🤖 راه‌اندازی ربات تلگرام")
    print("=" * 50)
    
    check_python_version()
    install_requirements()
    check_env_file()
    
    print("\n" + "=" * 50)
    print("✅ راه‌اندازی کامل شد!")
    print("=" * 50)
    print("\n🚀 برای اجرای بات دستور زیر را وارد کنید:")
    print("   python main.py")
    print("\n💡 برای توقف بات از Ctrl+C استفاده کنید.")


if __name__ == "__main__":
    main()
