from app.models import UserDrop

STANDARD_5_STAR_CHARACTERS_EVENT_BANNER = [
    "Diluc", "Jean", "Qiqi", "Mona", "Keqing", "Tighnari", "Dehya"
]

# Максимальные значения pity (хард-пити)
PITY_LIMITS = {
    'character_event': {'5_star': 90, '4_star': 10},
    'weapon_event': {'5_star': 80, '4_star': 10},
    'standard': {'5_star': 90, '4_star': 10},
    'beginner': {'5_star': 20, '4_star': 10}  # У Beginner Wish свои правила, 5* часто раньше 20
}

# Маппинг gacha_type ID на banner_group для Genshin Impact
GENSHIN_GACHA_TYPE_TO_BANNER_GROUP = {
    '100': 'beginner',
    '200': 'standard',
    '301': 'character_event',
    '400': 'character_event',  # Делит pity с 301
    '302': 'weapon_event'
}


class GenshinPityTracker:
    def __init__(self, user, game):
        """
        user: объект User (из Flask-Login current_user)
        game: объект Game (для Genshin Impact)
        """
        if game.slug != 'genshin':
            raise ValueError("GenshinPityTracker предназначен только для игры Genshin Impact.")
        self.user = user
        self.game = game
        self.all_user_drops_for_game = self._get_all_user_drops_for_game()
        self.banner_states = {}

    def _get_all_user_drops_for_game(self):
        """Загружает все дропы пользователя для данной игры один раз и сортирует."""
        return UserDrop.query.filter(
            UserDrop.user_id == self.user.id,
            UserDrop.game_id == self.game.id
        ).order_by(UserDrop.timestamp.asc()).all()  # ASC для корректной итерации при расчете pity

    def _get_banner_group_for_drop(self, drop):
        """Определяет banner_group для конкретного дропа."""
        return GENSHIN_GACHA_TYPE_TO_BANNER_GROUP.get(drop.lootbox_type.game_specific_id)

    def _filter_drops_for_banner_group(self, banner_group_name):
        """Фильтрует предварительно загруженные дропы для указанной группы баннеров."""
        filtered_drops = []
        for drop in self.all_user_drops_for_game:
            group = self._get_banner_group_for_drop(drop)
            if group == banner_group_name:
                filtered_drops.append(drop)
        return filtered_drops  # Уже отсортированы по timestamp.asc()

    def calculate_all_banner_states(self):
        """Рассчитывает состояние для всех основных групп баннеров."""
        self.banner_states['character_event'] = self._calculate_character_event_state()
        self.banner_states['weapon_event'] = self._calculate_weapon_event_state()
        self.banner_states['standard'] = self._calculate_standard_state()
        # self.banner_states['beginner'] = self._calculate_beginner_state() # Можно добавить
        return self.banner_states

    def _calculate_character_event_state(self):
        state = {
            'pity5_count': 0,
            'pity4_count': 0,
            'lose50_active': False,  # True если следующий 5* гарантированно ивентовый
            'history_5_star': [],
            'total_pulls': 0,
            'wins_50_50': 0,
            'losses_50_50': 0,
            'avg_pity_5_star': 0
        }
        drops = self._filter_drops_for_banner_group('character_event')
        state['total_pulls'] = len(drops)
        if not drops: return state

        _internal_lose50_flag_for_next_guarantee = False
        pity_sum_5_star = 0
        count_5_star_for_avg = 0

        for drop in drops:
            state['pity4_count'] += 1
            state['pity5_count'] += 1

            if drop.item_rarity_text == '5':
                pity_at_hit = state['pity5_count']
                pity_sum_5_star += pity_at_hit
                count_5_star_for_avg += 1

                is_standard_char = drop.item_name in STANDARD_5_STAR_CHARACTERS_EVENT_BANNER
                won_50_50_this_drop = None
                was_guarantee_this_drop = False

                if _internal_lose50_flag_for_next_guarantee:
                    was_guarantee_this_drop = True
                    _internal_lose50_flag_for_next_guarantee = False
                else:
                    if not is_standard_char:
                        won_50_50_this_drop = True
                        state['wins_50_50'] += 1
                        _internal_lose50_flag_for_next_guarantee = False
                    else:
                        won_50_50_this_drop = False
                        state['losses_50_50'] += 1
                        _internal_lose50_flag_for_next_guarantee = True

                state['history_5_star'].append({
                    'pity_at': pity_at_hit,
                    'item_name': drop.item_name,
                    'timestamp': drop.timestamp,
                    'won_50_50': won_50_50_this_drop,
                    'was_guarantee': was_guarantee_this_drop,
                    'is_standard_char_on_event_banner': is_standard_char
                })
                state['pity5_count'] = 0
                state['pity4_count'] = 0

            elif drop.item_rarity_text == '4':
                state['pity4_count'] = 0

        state['lose50_active'] = _internal_lose50_flag_for_next_guarantee
        if count_5_star_for_avg > 0:
            state['avg_pity_5_star'] = round(pity_sum_5_star / count_5_star_for_avg, 1)
        return state

    def _calculate_generic_banner_state(self, banner_group_name):
        """Общая функция для Standard и Weapon (пока без Epitomized Path)"""
        state = {
            'pity5_count': 0,
            'pity4_count': 0,
            'history_5_star': [],
            'total_pulls': 0,
            'avg_pity_5_star': 0
            # Для weapon_event можно будет добавить fate_points и т.д.
        }
        if banner_group_name == 'weapon_event':
            state['fate_points'] = 0  # Заглушка
            state['selected_epitome_item_name'] = None  # Заглушка

        drops = self._filter_drops_for_banner_group(banner_group_name)
        state['total_pulls'] = len(drops)
        if not drops: return state

        pity_sum_5_star = 0
        count_5_star_for_avg = 0

        for drop in drops:
            state['pity4_count'] += 1
            state['pity5_count'] += 1

            if drop.item_rarity_text == '5':
                pity_at_hit = state['pity5_count']
                pity_sum_5_star += pity_at_hit
                count_5_star_for_avg += 1
                state['history_5_star'].append({
                    'pity_at': pity_at_hit,
                    'item_name': drop.item_name,
                    'timestamp': drop.timestamp
                    # Для weapon_event здесь будет логика Epitomized Path
                })
                state['pity5_count'] = 0
                state['pity4_count'] = 0
            elif drop.item_rarity_text == '4':
                state['pity4_count'] = 0

        if count_5_star_for_avg > 0:
            state['avg_pity_5_star'] = round(pity_sum_5_star / count_5_star_for_avg, 1)
        return state

    def _calculate_weapon_event_state(self):
        # Пока что используем общую логику, потом доработаем Epitomized Path
        # Эта функция будет сложнее, когда добавим отслеживание fate_points
        # и featured оружия с помощью таблиц Banner/BannerItem
        state = self._calculate_generic_banner_state('weapon_event')
        # Здесь в будущем будет логика для fate_points, если мы сможем определить featured
        # и пользователь будет выбирать цель.
        # Пока оставляем fate_points = 0 как заглушку.
        return state

    def _calculate_standard_state(self):
        return self._calculate_generic_banner_state('standard')

    # def _calculate_beginner_state(self):
    #     # Упрощенный, т.к. всего 20 круток и свои гаранты
    #     # ...
    #     pass

    def get_overall_stats(self):
        """Собирает общую статистику по всем дропам игры."""
        if not self.all_user_drops_for_game:
            return {'3': 0, '4': 0, '5': 0}, 0

        rarity_counts = {'3': 0, '4': 0, '5': 0}
        for drop in self.all_user_drops_for_game:
            if drop.item_rarity_text in rarity_counts:
                rarity_counts[drop.item_rarity_text] += 1
            else:  # На случай если в данных будет другая редкость
                rarity_counts[drop.item_rarity_text] = 1

        total_pulls = len(self.all_user_drops_for_game)
        return rarity_counts, total_pulls

    def get_latest_drops(self, limit=10):
        """Возвращает последние N дропов."""
        # all_user_drops_for_game уже отсортированы по timestamp.asc()
        # поэтому берем срез с конца
        return self.all_user_drops_for_game[-limit:][::-1]  # Срез и реверс для desc() порядка
