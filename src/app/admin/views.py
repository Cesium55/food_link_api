from sqladmin import BaseView, expose


class ReportView(BaseView):
    name = "Report Page"
    icon = "fa-solid fa-chart-line"

    @expose("/report", methods=["GET"])
    async def report_page(self, request):
        return await self.templates.TemplateResponse(request, "example.html")
    
