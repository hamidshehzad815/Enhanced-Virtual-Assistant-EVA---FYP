class IntegrationModel {
  final String provider;
  final bool isActive;
  final String? calendarId;
  final DateTime? lastSyncedAt;

  const IntegrationModel({
    required this.provider,
    required this.isActive,
    this.calendarId,
    this.lastSyncedAt,
  });

  factory IntegrationModel.fromJson(Map<String, dynamic> json) {
    return IntegrationModel(
      provider: json['provider']?.toString() ?? '',
      isActive: json['is_active'] == true,
      calendarId: json['calendar_id']?.toString(),
      lastSyncedAt: json['last_synced_at'] != null
          ? DateTime.tryParse(json['last_synced_at'].toString())
          : null,
    );
  }

  bool get isGoogleCalendar =>
      provider.toLowerCase() == 'google_calendar' && isActive;
}
