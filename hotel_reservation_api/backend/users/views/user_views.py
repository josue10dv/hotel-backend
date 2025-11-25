from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from backend.users.serializers import UserRegistrationSerializer


class UserRegistrationView(APIView):
    """
    API endpoint for user registration.
    Accepts POST requests with username, email, password, and password_confirm.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Register a new user.
        
        Expected payload:
        {
            "username": "string",
            "email": "string",
            "password": "string",
            "password_confirm": "string"
        }
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User registered successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
