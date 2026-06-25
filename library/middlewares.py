import time

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.tokens import TokenError, AccessToken, RefreshToken
from rest_framework_simplejwt.settings import api_settings

from library.utils import clear_cookies, set_access_token


# class TestRequestNotificationMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request: HttpRequest, *args, **kwargs):
#         # Работаем с самим request можно что-то сделать перед тем, как получим ответ
#
#         print("=" * 100)
#         print("[TestRequestNotificationMiddleware] INCOMING REQUEST!!!!!!!!")
#         print(f"REQUEST METHOD: {request.method}")
#         print(f"REQUEST PATH: {request.path}")
#         print(f"REQUEST FULL PATH: {request.get_full_path()}")
#         print(f"FROM ANONYMOUS: {request.user is not None}")
#         print("=" * 100)
#
#         response = self.get_response(request)
#
#         # можно что-то сделать ПОСЛЕ того, как получим ответ
#         print("=" * 100)
#         print("[TestRequestNotificationMiddleware] OUTGOING RESPONSE!!!!!!!!")
#         print(f"REQUEST FULL PATH: {response.status_code}")
#         print(f"RESPONSE DATA: {response.data}")
#         print("=" * 100)
#
#         return response

class JWTAuthMiddleware:
    # Эти маршруты исключаем из обработки полностью,
    # чтобы middleware не вмешивался в точки входа, где auth-логика должна жить отдельно.
    excluded_paths = {
        "/auth-login/",
        "/auth-register/",
        "/refresh-token/",
        "/jwt-login/",
    }

    # Для некоторых групп путей удобнее исключать не одно точное значение,
    # а сразу целый префикс.
    excluded_path_prefixes = (
        "/admin/",
        "/api-auth/",
    )

    # В современном middleware Django сюда приходит следующий обработчик,
    # которому мы передадим запрос после своей подготовки.
    def __init__(self, get_response):
        # Сохраняем следующий шаг цепочки обработки запроса.
        self.get_response = get_response

        # Окно для "раннего" обновления access рассчитываем один раз при создании middleware,
        # чтобы не пересчитывать его на каждый запрос.
        self.refresh_window_seconds = self._build_refresh_window_seconds()

    # Через __call__ middleware работает и на входе, и на выходе:
    # сначала подготавливает request, потом получает response и при необходимости меняет его.
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Если путь исключён, просто пропускаем запрос дальше без JWT-обработки.
        if self._should_skip(request):
            return self.get_response(request)

        # Получаем access и refresh из cookies запроса.
        access_token = self._get_access_cookie(request)
        refresh_token = self._get_refresh_cookie(request)

        # Здесь запомним новый access, если выпустим его по refresh.
        minted_access_token: str | None = None

        # Этот флаг нужен, чтобы после обработки запроса централизованно решить,
        # нужно ли очистить auth cookies как невалидные.
        should_clear_auth_cookies = False

        # Вся дальнейшая JWT-логика имеет смысл только если у клиента вообще есть auth cookies.
        if self._has_auth_cookies(access_token, refresh_token):

            # Если refresh уже невалиден, считаем auth-сессию сломанной
            # и готовим очистку cookies на ответе.
            if not self._is_refresh_token_valid(refresh_token):
                should_clear_auth_cookies = True

            # Если refresh живой, а access ещё не подходит к истечению,
            # просто используем текущий access для этого запроса.
            elif access_token and not self._is_access_expiring(access_token):
                self._set_authorization_header(request, access_token)

            # Во всех остальных случаях пробуем выпустить новый access по refresh.
            else:
                minted_access_token = self._mint_access_token(refresh_token)

                # Если новый access удалось выпустить,
                # сразу подставляем его в текущий запрос.
                if minted_access_token:
                    self._set_authorization_header(request, minted_access_token)

                # Если даже по валидному refresh access выпустить не удалось,
                # считаем состояние токенов неконсистентным и очищаем cookies.
                else:
                    should_clear_auth_cookies = True

        # После всей подготовительной логики передаём запрос дальше по цепочке.
        response = self.get_response(request)

        # Если токены признаны сломанными, очищаем auth cookies на ответе.
        if should_clear_auth_cookies:
            clear_cookies(response)

        # Если в ходе запроса был выпущен новый access,
        # обновляем его в cookie ответа.
        elif minted_access_token:
            set_access_token(response, minted_access_token)

        # Возвращаем итоговый ответ клиенту.
        return response

    # Размер окна раннего обновления access рассчитываем динамически,
    # чтобы он зависел от реального времени жизни токена, а не был жёстко захардкожен.
    def _build_refresh_window_seconds(self) -> int:
        # Берём lifetime access token в секундах из настроек SimpleJWT.
        access_lifetime_seconds = int(
            api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()
        )

        # Дальше выбираем четверть от этого времени,
        # но оставляем значение в разумных границах.
        return max(1, min(30, access_lifetime_seconds // 4))

    # Проверку исключённых путей выносим отдельно,
    # чтобы основной сценарий в __call__ читался проще.
    def _should_skip(self, request: HttpRequest) -> bool:
        # Пропускаем middleware либо для точных путей,
        # либо для путей с исключёнными префиксами.
        return request.path in self.excluded_paths or request.path.startswith(
            self.excluded_path_prefixes
        )

    # Отдельно оформляем проверку наличия auth cookies,
    # чтобы в основном сценарии работать уже с понятным условием верхнего уровня.
    def _has_auth_cookies(
        self,
        access_token: str | None,
        refresh_token: str | None,
    ) -> bool:
        # Если есть хотя бы один из токенов, значит auth-состояние у клиента присутствует.
        return bool(access_token or refresh_token)

    # Получение access выносим в отдельный метод,
    # чтобы не привязывать основной сценарий к деталям request.COOKIES.
    def _get_access_cookie(self, request: HttpRequest) -> str | None:
        # Возвращаем access_token или None, если cookie нет.
        return request.COOKIES.get("access_token")

    # Получение refresh оформляем так же,
    # чтобы оба токена читались одинаково и предсказуемо.
    def _get_refresh_cookie(self, request: HttpRequest) -> str | None:
        # Возвращаем refresh_token или None, если cookie нет.
        return request.COOKIES.get("refresh_token")

    # Подстановку Authorization выносим отдельно,
    # чтобы не дублировать Bearer-формат в разных ветках.
    def _set_authorization_header(
        self,
        request: HttpRequest,
        access_token: str,
    ) -> None:
        # Формируем стандартный Authorization header для DRF / SimpleJWT.
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

    # Валидность refresh проверяем отдельно,
    # потому что от него зависит, можно ли вообще продолжать auth-сценарий.
    def _is_refresh_token_valid(self, refresh_token: str | None) -> bool:
        # Без refresh проверка сразу считается неуспешной.
        if not refresh_token:
            return False

        # Любая работа с JWT может падать на битом, просроченном или отозванном токене,
        # поэтому проверяем это безопасно.
        try:
            # Если RefreshToken успешно создаётся, считаем refresh валидным.
            RefreshToken(refresh_token)
            return True

        # Ожидаемый сценарий невалидного refresh.
        except TokenError:
            return False

        # Любую другую ошибку тоже трактуем как невалидность токена.
        except Exception:
            return False

    # Выпуск нового access по refresh — это отдельная задача,
    # поэтому держим её в отдельном методе.
    def _mint_access_token(self, refresh_token: str | None) -> str | None:
        # Без refresh выпустить новый access невозможно.
        if not refresh_token:
            return None

        # Безопасно обрабатываем все сценарии битого или просроченного refresh.
        try:
            # Превращаем строку refresh в объект токена.
            refresh = RefreshToken(refresh_token)

            # Выпускаем на его основе новый access и возвращаем его как строку.
            return str(refresh.access_token)

        # Ожидаемый сценарий, когда refresh уже нельзя использовать.
        except TokenError:
            return None

        # Любую другую ошибку тоже не пробрасываем наружу.
        except Exception:
            return None

    # Проверку срока жизни access выносим отдельно,
    # потому что это самостоятельное условие для решения: использовать токен или обновлять.
    def _is_access_expiring(self, access_token: str) -> bool:
        # Пытаемся прочитать exp из токена.
        try:
            # Разбираем строку как AccessToken.
            token = AccessToken(access_token)

            # Берём время истечения токена в Unix-формате.
            exp_timestamp = int(token["exp"])

            # Получаем текущее время в том же формате.
            now_timestamp = int(time.time())

            # Если токен истекает в пределах окна обновления,
            # считаем, что его уже пора перевыпускать.
            return exp_timestamp <= now_timestamp + self.refresh_window_seconds

        # Если токен не удалось корректно прочитать,
        # безопаснее считать его неподходящим для дальнейшего использования.
        except Exception:
            return True
