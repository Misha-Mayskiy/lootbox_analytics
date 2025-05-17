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
        return filtered_drops

    def calculate_all_banner_states(self):
        """Рассчитывает состояние для всех основных групп баннеров."""
        self.banner_states['character_event'] = self._calculate_character_event_state()
        self.banner_states['weapon_event'] = self._calculate_weapon_event_state()
        self.banner_states['standard'] = self._calculate_standard_state()
        return self.banner_states

    def _calculate_character_event_state(self):
        state = {
            'pity5_count': 0,
            'pity4_count': 0,
            'lose50_active': False,
            'history_5_star': [],
            'total_pulls': 0,
            'wins_50_50': 0,
            'losses_50_50': 0,
            'win_rate_50_50': 0,
            'avg_pity_5_star': 0,
            'pity_luck_5_star': {}
        }

        drops = self._filter_drops_for_banner_group('character_event')
        state['total_pulls'] = len(drops)
        if not drops: return state

        _internal_lose50_flag_for_next_guarantee = False
        pity_sum_5_star = 0

        for drop in drops:
            state['pity4_count'] += 1
            state['pity5_count'] += 1

            if drop.item_rarity_text == '5':
                pity_at_hit = state['pity5_count']
                pity_sum_5_star += pity_at_hit

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

        # Расчет среднего pity и процента выигрыша 50/50
        total_50_50_outcomes = state['wins_50_50'] + state['losses_50_50']
        if total_50_50_outcomes > 0:
            state['win_rate_50_50'] = round((state['wins_50_50'] / total_50_50_outcomes) * 100, 1)

        if state['history_5_star']:
            state['avg_pity_5_star'] = round(pity_sum_5_star / len(state['history_5_star']), 1)
            state['pity_luck_5_star'] = self._analyze_pity_luck(state['history_5_star'],
                                                                soft_pity_start=74,
                                                                hard_pity_limit=PITY_LIMITS['character_event'][
                                                                    '5_star'])
        return state

    def _calculate_generic_banner_state(self, banner_group_name):
        state = {
            'pity5_count': 0,
            'pity4_count': 0,
            'history_5_star': [],
            'total_pulls': 0,
            'avg_pity_5_star': 0,
            'pity_luck_5_star': {}
        }
        if banner_group_name == 'weapon_event':
            state['fate_points'] = 0
            state['selected_epitome_item_name'] = None

        drops = self._filter_drops_for_banner_group(banner_group_name)
        state['total_pulls'] = len(drops)
        if not drops: return state

        pity_sum_5_star = 0

        for drop in drops:
            state['pity4_count'] += 1
            state['pity5_count'] += 1

            if drop.item_rarity_text == '5':
                pity_at_hit = state['pity5_count']
                pity_sum_5_star += pity_at_hit
                state['history_5_star'].append({
                    'pity_at': pity_at_hit,
                    'item_name': drop.item_name,
                    'timestamp': drop.timestamp
                })
                state['pity5_count'] = 0
                state['pity4_count'] = 0
            elif drop.item_rarity_text == '4':
                state['pity4_count'] = 0

        if state['history_5_star']:
            state['avg_pity_5_star'] = round(pity_sum_5_star / len(state['history_5_star']), 1)
            soft_pity_start = 0
            if banner_group_name == 'weapon_event':
                soft_pity_start = 62
            elif banner_group_name == 'standard':
                soft_pity_start = 74

            if soft_pity_start > 0:
                state['pity_luck_5_star'] = self._analyze_pity_luck(state['history_5_star'],
                                                                    soft_pity_start=soft_pity_start,
                                                                    hard_pity_limit=PITY_LIMITS[banner_group_name][
                                                                        '5_star'])
        return state

    def _calculate_weapon_event_state(self):
        state = self._calculate_generic_banner_state('weapon_event')
        return state

    def _calculate_standard_state(self):
        return self._calculate_generic_banner_state('standard')

    def get_overall_stats(self):
        """Собирает общую статистику по всем дропам игры."""
        if not self.all_user_drops_for_game:
            return {'3': 0, '4': 0, '5': 0}, 0

        rarity_counts = {'3': 0, '4': 0, '5': 0}
        for drop in self.all_user_drops_for_game:
            if drop.item_rarity_text in rarity_counts:
                rarity_counts[drop.item_rarity_text] += 1
            else:
                rarity_counts[drop.item_rarity_text] = 1

        total_pulls = len(self.all_user_drops_for_game)
        return rarity_counts, total_pulls

    def get_latest_drops(self, limit=10):
        """Возвращает последние N дропов."""
        return self.all_user_drops_for_game[-limit:][::-1]

    def _analyze_pity_luck(self, history_5_star, soft_pity_start, hard_pity_limit):
        """Анализирует историю 5* дропов на предмет ранних/поздних выпадений."""
        if not history_5_star:
            return {'early': 0, 'soft_pity_zone': 0, 'hard_pity': 0, 'total': 0}

        luck_stats = {'early': 0, 'soft_pity_zone': 0, 'hard_pity': 0, 'total': len(history_5_star)}
        for drop_info in history_5_star:
            pity = drop_info['pity_at']
            if pity < soft_pity_start:
                luck_stats['early'] += 1
            elif pity < hard_pity_limit:
                luck_stats['soft_pity_zone'] += 1
            else:
                luck_stats['hard_pity'] += 1
        return luck_stats
