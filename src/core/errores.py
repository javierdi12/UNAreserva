"""Excepciones propias de la capa CRUD."""


class ErrorValidacion(Exception):
    """Datos invalidos o regla de negocio incumplida."""


class NoEncontrado(Exception):
    """El documento solicitado no existe."""