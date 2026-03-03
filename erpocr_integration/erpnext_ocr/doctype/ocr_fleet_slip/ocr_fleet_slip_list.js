frappe.listview_settings['OCR Fleet Slip'] = {
	get_indicator: function(doc) {
		var status_map = {
			"Pending": [__("Pending"), "blue", "status,=,Pending"],
			"Needs Review": [__("Needs Review"), "orange", "status,=,Needs Review"],
			"Matched": [__("Matched"), "blue", "status,=,Matched"],
			"Draft Created": [__("Draft Created"), "purple", "status,=,Draft Created"],
			"Completed": [__("Completed"), "green", "status,=,Completed"],
			"No Action": [__("No Action"), "grey", "status,=,No Action"],
			"Error": [__("Error"), "red", "status,=,Error"],
		};
		return status_map[doc.status] || [__(doc.status), "grey", "status,=," + doc.status];
	}
};
