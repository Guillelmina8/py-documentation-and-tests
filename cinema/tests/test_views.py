from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Movie Title",
        "description": "Movie Description",
        "duration": 105,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)

def image_upload_url(movie_id):
    return reverse("cinema:movie-upload_image", args=[movie_id])


class UnauthenticatedMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_genres_list(self):
        sample_movie()
        movie_with_genre = sample_movie()

        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Fantasy")

        movie_with_genre.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_actors_list(self):
        sample_movie()
        movie_with_actor = sample_movie()

        actor_1 = Actor.objects.create(first_name="Keanu", last_name="Reeves")
        actor_2 = Actor.objects.create(first_name="Jennifer", last_name="Lawrence")

        movie_with_actor.actors.add(actor_1, actor_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Funny Movie")
        movie_with_genre_2 = sample_movie(title="Interesting Movie")

        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Fantasy")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre, many=True)
        serializer_movie_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_genre_1.data, res.data)
        self.assertIn(serializer_movie_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genre, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="Brave Movie")
        movie_with_actor_2 = sample_movie(title="Interesting Movie")

        actor_1 = Actor.objects.create(first_name="Keanu", last_name="Reeves")
        actor_2 = Actor.objects.create(first_name="Jennifer", last_name="Lawrence")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_movie_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_movie_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_movie_actor_1.data, res.data)
        self.assertIn(serializer_movie_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actor, res.data)

    def test_retrieve_movie_details(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Comedy"))
        movie.actors.add(Actor.objects.create(first_name="Jennifer", last_name="Lawrence"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 105,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 105,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Fantasy")
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 105,
            "genres": [genre_1.id, genre_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
