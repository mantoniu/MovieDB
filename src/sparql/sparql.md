## SPARQL Queries

# Query 1

Quels sont les 30 films ayant au moins 50 avis qui sont les plus “polarisants”, c’est-à-dire ceux qui ont à la fois une forte proportion de notes basses (≤ 3) et une forte proportion de notes hautes (≥ 8), classés par une polarisation pondérée par le nombre total d’avis ?

```sparql
prefix : <http://www.moviedb.fr/cinema#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>

select ?movie ?title ?nReviews ?polarization ?polarizationWeighted
where {
  {
    select ?movie ?title
           (count(?r) as ?nReviews)
           (
             (xsd:decimal(sum(?isLow)) / xsd:decimal(count(?r)))
             * (xsd:decimal(sum(?isHigh)) / xsd:decimal(count(?r)))
             as ?polarization
           )
           (
             (
               (xsd:decimal(sum(?isLow)) / xsd:decimal(count(?r)))
               * (xsd:decimal(sum(?isHigh)) / xsd:decimal(count(?r)))
             )
             * xsd:decimal(count(?r))
             as ?polarizationWeighted
           )
    where {
      ?movie :primaryTitle ?title .
      ?r a :Review ; :isReviewOf ?movie ; :ratingValue ?rating .
      bind(if(?rating <= 3, 1, 0) as ?isLow)
      bind(if(?rating >= 8, 1, 0) as ?isHigh)
    }
    group by ?movie ?title
    having (count(?r) >= 50)
  }
}
order by desc(?polarizationWeighted)
limit 30
```

# Query 2

Quels réalisateurs sont associés à des films dont les critiques sont, en moyenne, jugées les plus utiles par les utilisateurs ?

```sparql
prefix : <http://www.moviedb.fr/cinema#>

select ?directorName ?nMovies ?nReviews ?avgHelp
where {
  {
    select ?director ?directorName
           (count(distinct ?movie) as ?nMovies)
           (count(?r) as ?nReviews)
           (avg(?help) as ?avgHelp)
    where {
      ?movie a :MotionPicture ;
             :hasDirector ?director .
      ?director :name ?directorName .
      ?r a :Review ;
         :isReviewOf ?movie ;
         :helpfulnessVote ?help .
    }
    group by ?director ?directorName
    having (count(distinct ?movie) >= 2 && count(?r) >= 100)
  }
}
order by desc(?avgHelp) desc(?nReviews)
limit 30
```

# Query 3

L’ontologie permet-elle d’identifier les acteurs dont les films reçoivent, en moyenne, les évaluations les plus élevées de la part des utilisateurs ?

```sparql
prefix : <http://www.moviedb.fr/cinema#>

select ?actor ?actorName ?nMovies ?nReviews ?avgRating
where {
  {
    select ?actor
           (sample(?name0) as ?actorName)
           (count(distinct ?movie) as ?nMovies)
           (count(?r) as ?nReviews)
           (avg(?rating) as ?avgRating)
    where {
      ?movie a :MotionPicture ;
             :hasActor ?actor .

      ?r a :Review ;
         :isReviewOf ?movie ;
         :ratingValue ?rating .

      optional { ?actor :name ?name0 . }
    }
    group by ?actor
    having (count(distinct ?movie) >= 5 && count(?r) >= 200)
  }
}
order by desc(?avgRating) desc(?nMovies) desc(?nReviews)
limit 50
```

# Query 4

Quels sont les 30 réalisateurs dont les films ont reçu le plus d’avis positifs (contenant des mots comme “chef-d’œuvre”, “incroyable”, “parfait”) par rapport aux avis négatifs (contenant des mots comme “terrible”, “affreux”, “ennuyeux”, “perte de temps”) ?

```sparql
prefix : <http://www.moviedb.fr/cinema#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>

select ?director ?directorName ?nReviews ?nPositive ?nNegative
       (xsd:decimal(?nPositive) / xsd:decimal(?nReviews) as ?positiveRatio)
       (xsd:decimal(?nNegative) / xsd:decimal(?nReviews) as ?negativeRatio)
where {
  {
    select ?director
           (sample(?name0) as ?directorName)
           (count(?review) as ?nReviews)
           (sum(?isPositive) as ?nPositive)
           (sum(?isNegative) as ?nNegative)
    where {
      ?review :isReviewOf ?movie ;
              :reviewBody ?reviewBody .
      ?movie :hasDirector ?director .
      optional { ?director :name ?name0 . }

      bind(
        if(regex(str(?reviewBody), "(masterpiece|amazing|perfect)", "i"), 1, 0)
        as ?isPositive
      )

      bind(
        if(regex(str(?reviewBody), "(terrible|awful|boring|waste)", "i"), 1, 0)
        as ?isNegative
      )
    }
    group by ?director
    having (count(?review) >= 100)
  }
}
order by desc(?positiveRatio) desc(?negativeRatio)
limit 30
```