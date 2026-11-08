# QUANTEX Free Intelligence Engine

محرك معلومات مجاني مصاحب لمؤشر TradingView. يجمع:
- أخبار آخر 48 ساعة من GDELT.
- تحويلات Bitcoin كبيرة من الكتل الحديثة عبر mempool.space.
- Open Interest وFunding Rate وحجم تداول BTCUSDT من Binance USD-M public market data.
- لوحة ويب ثابتة تُنشر عبر GitHub Pages.

## حدود مهمة
1. هذا المشروع لا يرسل بيانات إلى Pine Script. لوحة الويب منفصلة عن TradingView.
2. تحويل BTC كبير لا يعني تلقائياً شراء حوت أو بيع حوت. لا توجد هنا هوية مؤكدة للمحافظ أو تصنيف exchange inflow/outflow.
3. عدّ الأخبار لا يساوي تحليل مشاعر أو أثر اقتصادي. العناوين تعرض للمراجعة ولا تنتج BUY/SELL آلياً.
4. لا توجد بيانات ETF أو محافظ موسومة أو تصفيات شاملة في هذا الإصدار.
5. GitHub Actions المجاني له حدود استخدام؛ الجدولة كل 30 دقيقة قد تتأخر، وواجهات API العامة قد تتعطل أو تحد الطلبات.
6. لا تستخدم هذه البيانات كإشارة تداول آلية أو ضمان ربح.

## النشر
1. أنشئ مستودع GitHub جديداً باسم `quantex-free-intelligence` واجعله Public.
2. ارفع جميع ملفات هذا المجلد إلى جذر المستودع مع الحفاظ على مجلد `.github/workflows`.
3. من Settings → Pages اختر Deploy from a branch، ثم `main` و`/site`.
4. من Actions شغّل `Update QUANTEX public intelligence data` يدوياً أول مرة.
5. بعد نجاح التشغيل، افتح رابط GitHub Pages الخاص بالمستودع.

لا يحتاج هذا الإعداد إلى مفاتيح API أو اشتراكات مدفوعة في نسخته الأولية.
