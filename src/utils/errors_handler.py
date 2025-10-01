from functools import wraps
from typing import Callable, Any
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from sqlalchemy.orm import exc as orm_exc
from fastapi import HTTPException, status


def handle_alchemy_error(func: Callable) -> Callable:
    """
    Decorator to handle SQLAlchemy errors and convert them to HTTP exceptions.
    
    Usage:
        @handle_alchemy_error
        async def some_manager_method(self, ...):
            # Your method logic here
            pass
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs) -> Any:
        try:
            return await func(self, *args, **kwargs)
        except orm_exc.NoResultFound as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        except orm_exc.MultipleResultsFound as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Multiple results found when single result expected"
            )
        except IntegrityError as e:
            error_message = str(e).lower()
            if "unique" in error_message or "duplicate" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Resource with this data already exists"
                )
            elif "foreign key" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot perform operation due to foreign key constraints"
                )
            elif "check" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data validation failed"
                )
            elif "not null" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Required field cannot be null"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data integrity constraint violation"
                )
        except DataError as e:
            error_message = str(e).lower()
            if "numeric" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid numeric data format"
                )
            elif "string data right truncation" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data too long for field"
                )
            elif "invalid datetime" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid datetime format"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid data format"
                )
        except OperationalError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable"
            )
        except Exception as e:
            # Re-raise non-SQLAlchemy exceptions
            raise e
    
    return wrapper
