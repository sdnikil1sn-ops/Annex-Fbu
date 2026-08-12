/// Backend API abstraction for the analysis and i18n endpoints.
///
/// The app depends on [AnalysisApi]; production uses [HttpAnalysisApi],
/// tests use the explicit mock (CONTRIBUTING: mocks never ship in prod
/// paths and are named `Mock*`).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_models/shared_models.dart';

/// Thrown when the backend answers outside the expected envelope.
class ApiException implements Exception {
  const ApiException(this.code, this.message);

  /// Machine-readable error code from the envelope (e.g. `analysis.not_found`).
  final String code;
  final String message;

  @override
  String toString() => 'ApiException($code): $message';
}

/// The backend surface the app consumes.
abstract interface class AnalysisApi {
  /// Submit text for analysis; returns the created (pending) analysis.
  Future<Analysis> submitText(String text, {String locale = 'en'});

  /// Fetch an analysis by id (polling).
  Future<Analysis> fetchAnalysis(String id);

  /// The enabled locales with their fallback parents.
  Future<LocaleList> fetchLocales();

  /// A resolved translation bundle for a locale.
  Future<TranslationBundle> fetchBundle(String locale);
}

/// HTTP implementation against the v1 backend API.
class HttpAnalysisApi implements AnalysisApi {
  HttpAnalysisApi({
    required this.baseUrl,
    http.Client? client,
    this.tokenProvider,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  /// Supplies the Firebase ID token for the Authorization header, or null
  /// for anonymous requests.
  final String? Function()? tokenProvider;

  @override
  Future<Analysis> submitText(String text, {String locale = 'en'}) async {
    final json = await _post('/analysis', {
      'input_type': 'text',
      'text': text,
      'locale': locale,
    });
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'analysis.invalid_response',
        'Malformed analysis response',
      );
    }
    return Analysis.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<Analysis> fetchAnalysis(String id) async {
    final json = await _get('/analysis/$id');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'analysis.invalid_response',
        'Malformed analysis response',
      );
    }
    return Analysis.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<LocaleList> fetchLocales() async {
    final json = await _get('/i18n/locales');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed locales response',
      );
    }
    return LocaleList.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<TranslationBundle> fetchBundle(String locale) async {
    final json = await _get('/i18n/bundles/$locale');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed bundle response',
      );
    }
    return TranslationBundle.fromJson(Map<String, dynamic>.from(data));
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client.get(_uri(path), headers: _headers());
    return _decode(response);
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.post(
      _uri(path),
      headers: {..._headers(), 'content-type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, String> _headers() {
    final token = tokenProvider?.call();
    return {
      if (token != null && token.isNotEmpty) 'authorization': 'Bearer $token',
      'accept': 'application/json',
    };
  }

  Map<String, dynamic> _decode(http.Response response) {
    Map<String, dynamic> body;
    try {
      body =
          jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      throw ApiException('api.invalid_response', 'Response was not valid JSON');
    }
    if (response.statusCode >= 400) {
      final error = body['error'];
      if (error is Map) {
        throw ApiException(
          error['code'] as String? ?? 'api.error',
          error['message'] as String? ?? 'Request failed',
        );
      }
      throw ApiException(
        'api.error',
        'Request failed (${response.statusCode})',
      );
    }
    return body;
  }
}
