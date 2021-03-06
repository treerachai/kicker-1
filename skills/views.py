from django.db.models import Max
from django.shortcuts import render
from django.http import HttpResponse
from skills.models import GameResult, Player
import trueskill


def recalc_trueskills():
    players = Player.objects.all()
    for player in players:
        player.trueskill_mu = 25.000
        player.trueskill_sigma = 8.333
    players_dict = {p.id: p for p in players}
    game_results = GameResult.objects.order_by('date_time')

    latest_games = []
    for result in game_results:
        winner_front = players_dict[result.winner_front.id]
        winner_back = players_dict[result.winner_back.id]
        loser_front = players_dict[result.loser_front.id]
        loser_back = players_dict[result.loser_back.id]

        winner_front_rating = trueskill.Rating(mu=winner_front.trueskill_mu, sigma=winner_front.trueskill_sigma)
        winner_back_rating = trueskill.Rating(mu=winner_back.trueskill_mu, sigma=winner_back.trueskill_sigma)
        loser_front_rating = trueskill.Rating(mu=loser_front.trueskill_mu, sigma=loser_front.trueskill_sigma)
        loser_back_rating = trueskill.Rating(mu=loser_back.trueskill_mu, sigma=loser_back.trueskill_sigma)

        (new_winner_front_rating, new_winner_back_rating), (new_loser_front_rating, new_loser_back_rating) = \
            trueskill.rate([[winner_front_rating, winner_back_rating], [loser_front_rating, loser_back_rating]], ranks=[0, 1])

        winner_front.trueskill_mu = new_winner_front_rating.mu
        winner_front.trueskill_sigma = new_winner_front_rating.sigma
        winner_front.trueskill_date_time = result.date_time

        winner_back.trueskill_mu = new_winner_back_rating.mu
        winner_back.trueskill_sigma = new_winner_back_rating.sigma
        winner_back.trueskill_date_time = result.date_time

        loser_front.trueskill_mu = new_loser_front_rating.mu
        loser_front.trueskill_sigma = new_loser_front_rating.sigma
        loser_front.trueskill_date_time = result.date_time

        loser_back.trueskill_mu = new_loser_back_rating.mu
        loser_back.trueskill_sigma = new_loser_back_rating.sigma
        loser_back.trueskill_date_time = result.date_time

        latest_games.append({'winner_front': winner_front.change(winner_front_rating.mu), 'winner_back': winner_back.change(winner_back_rating.mu), \
                'loser_front': loser_front.change(loser_front_rating.mu), 'loser_back': loser_back.change(loser_back_rating.mu), \
                'result': '6:%d' % result.loser_score, 'date': result.date_time})
    return latest_games


def update_trueskills():
    last_update = Player.objects.aggregate(Max('trueskill_date_time'))['trueskill_date_time__max']
    if last_update:
        new_game_results = GameResult.objects.filter(date_time__gt=last_update).order_by('date_time')
    else:
        new_game_results = GameResult.objects.order_by('date_time')
    for result in new_game_results:
        winner_front = result.winner_front
        winner_back = result.winner_back
        loser_front = result.loser_front
        loser_back = result.loser_back

        winner_front_rating = trueskill.Rating(mu=winner_front.trueskill_mu, sigma=winner_front.trueskill_sigma)
        winner_back_rating = trueskill.Rating(mu=winner_back.trueskill_mu, sigma=winner_back.trueskill_sigma)
        loser_front_rating = trueskill.Rating(mu=loser_front.trueskill_mu, sigma=loser_front.trueskill_sigma)
        loser_back_rating = trueskill.Rating(mu=loser_back.trueskill_mu, sigma=loser_back.trueskill_sigma)

        (new_winner_front_rating, new_winner_back_rating), (new_loser_front_rating, new_loser_back_rating) = \
            trueskill.rate([[winner_front_rating, winner_back_rating], [loser_front_rating, loser_back_rating]], ranks=[0, 1])

        winner_front.trueskill_mu = new_winner_front_rating.mu
        winner_front.trueskill_sigma = new_winner_front_rating.sigma
        winner_front.trueskill_date_time = result.date_time
        winner_front.save()

        winner_back.trueskill_mu = new_winner_back_rating.mu
        winner_back.trueskill_sigma = new_winner_back_rating.sigma
        winner_back.trueskill_date_time = result.date_time
        winner_back.save()

        loser_front.trueskill_mu = new_loser_front_rating.mu
        loser_front.trueskill_sigma = new_loser_front_rating.sigma
        loser_front.trueskill_date_time = result.date_time
        loser_front.save()

        loser_back.trueskill_mu = new_loser_back_rating.mu
        loser_back.trueskill_sigma = new_loser_back_rating.sigma
        loser_back.trueskill_date_time = result.date_time
        loser_back.save()


def table(request):
    update_trueskills()
    table = []
    for player in Player.objects.order_by('-trueskill_mu'):
        won_games = len(player.winner_front_game_results.all()) + len(player.winner_back_game_results.all())
        lost_games =len(player.loser_front_game_results.all()) + len(player.loser_back_game_results.all())
        table.append({'name': player.name(), 'num_games': won_games + lost_games, \
                'points': '%d:%d' % (won_games, lost_games), 'mu': player.trueskill_mu, 'sigma': player.trueskill_sigma, \
                'rank': player.trueskill_mu - 3 * player.trueskill_sigma})
    latest_games = recalc_trueskills()
    if len(latest_games) > 10:
        latest_games = latest_games[-10:]
    return render(request, 'skills/table.html', context={'table': table, 'latest_games': latest_games[::-1]})
